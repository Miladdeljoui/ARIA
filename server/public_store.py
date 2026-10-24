"""Persistence primitives for ARIA public accounts, subscriptions, and referrals.

Not wired into the HTTP API yet. This establishes SQLite schema and transactional
primitives for the next integration milestone. It does not authenticate users,
verify payments, or grant production access by itself.
"""
from __future__ import annotations
import os, secrets, sqlite3, time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_DB = Path(__file__).resolve().parent / "aria_public.db"

def _now() -> int:
    return int(time.time())

class PublicStore:
    """SQLite storage for public ARIA accounts and entitlement events."""
    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = str(path or os.getenv("ARIA_PUBLIC_DB", DEFAULT_DB))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level="IMMEDIATE")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS public_users (
                    id TEXT PRIMARY KEY, google_sub TEXT UNIQUE, email TEXT,
                    email_verified INTEGER NOT NULL DEFAULT 0,
                    display_name TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user','owner')),
                    status TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active','suspended','deleted')),
                    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES public_users(id),
                    plan TEXT NOT NULL CHECK(plan IN ('trial','pro','pro_plus')),
                    starts_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    source TEXT NOT NULL CHECK(source IN
                        ('trial','referral','manual_payment','gateway','owner')),
                    status TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active','expired','revoked')),
                    created_at INTEGER NOT NULL, CHECK(expires_at > starts_at)
                );
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user_expiry
                    ON subscriptions(user_id,status,expires_at);
                CREATE TABLE IF NOT EXISTS referral_codes (
                    user_id TEXT PRIMARY KEY REFERENCES public_users(id),
                    code TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS referrals (
                    id TEXT PRIMARY KEY, inviter_user_id TEXT NOT NULL REFERENCES public_users(id),
                    invited_user_id TEXT NOT NULL UNIQUE REFERENCES public_users(id),
                    code TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','qualified','rejected')),
                    qualified_at INTEGER, created_at INTEGER NOT NULL,
                    CHECK(inviter_user_id <> invited_user_id)
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES public_users(id),
                    plan TEXT NOT NULL CHECK(plan IN ('pro','pro_plus')),
                    amount_minor INTEGER NOT NULL CHECK(amount_minor > 0), currency TEXT NOT NULL,
                    method TEXT NOT NULL CHECK(method IN ('gateway','bank_transfer')),
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending','pending_review','paid','rejected','cancelled','refunded')),
                    provider_reference TEXT, admin_note TEXT,
                    reviewed_by TEXT REFERENCES public_users(id), reviewed_at INTEGER,
                    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS entitlement_events (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES public_users(id),
                    event_type TEXT NOT NULL, source_id TEXT,
                    starts_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL, UNIQUE(user_id,event_type,source_id)
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY, actor_user_id TEXT REFERENCES public_users(id),
                    action TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT,
                    details_json TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL
                );
            """)

    def create_user(self, google_sub: str, email: str = "",
                    email_verified: bool = False, display_name: str = "") -> tuple[str, bool]:
        """Create or return an account by verified Google subject, never by email."""
        if not google_sub or not google_sub.strip():
            raise ValueError("google_sub is required")
        now = _now()
        with self.connection() as db:
            row = db.execute("SELECT id FROM public_users WHERE google_sub=?",
                             (google_sub,)).fetchone()
            if row:
                db.execute("""UPDATE public_users SET email=?,email_verified=?,
                    display_name=?,updated_at=? WHERE id=?""",
                    (email, int(email_verified), display_name, now, row["id"]))
                return row["id"], False
            user_id = secrets.token_urlsafe(18)
            db.execute("""INSERT INTO public_users
                (id,google_sub,email,email_verified,display_name,role,status,created_at,updated_at)
                VALUES (?,?,?,?,?,'user','active',?,?)""",
                (user_id, google_sub, email, int(email_verified), display_name, now, now))
            return user_id, True

    def ensure_referral_code(self, user_id: str) -> str:
        with self.connection() as db:
            row = db.execute("SELECT code FROM referral_codes WHERE user_id=?",
                             (user_id,)).fetchone()
            if row:
                return row["code"]
            for _ in range(8):
                code = secrets.token_urlsafe(7).replace("-", "").replace("_", "")[:9].upper()
                try:
                    db.execute("INSERT INTO referral_codes(user_id,code,created_at) VALUES (?,?,?)",
                               (user_id, code, _now()))
                    return code
                except sqlite3.IntegrityError:
                    continue
            raise RuntimeError("could not allocate unique referral code")

    def has_active_pro(self, user_id: str, now: int | None = None) -> bool:
        now = _now() if now is None else int(now)
        with self.connection() as db:
            user = db.execute("SELECT role,status FROM public_users WHERE id=?",
                              (user_id,)).fetchone()
            if not user or user["status"] != "active":
                return False
            if user["role"] == "owner":
                return True
            return db.execute("""SELECT 1 FROM subscriptions
                WHERE user_id=? AND status='active' AND starts_at<=? AND expires_at>?
                LIMIT 1""", (user_id, now, now)).fetchone() is not None

    def grant_subscription(self, user_id: str, plan: str, duration_seconds: int,
                           source: str, source_id: str | None = None,
                           now: int | None = None) -> str:
        """Grant transactionally; caller must authorize the source first."""
        if plan not in {"trial","pro","pro_plus"}:
            raise ValueError("invalid plan")
        if source not in {"trial","referral","manual_payment","gateway","owner"}:
            raise ValueError("invalid source")
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        now = _now() if now is None else int(now)
        sub_id, event_id = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
        with self.connection() as db:
            user = db.execute("SELECT status FROM public_users WHERE id=?",
                              (user_id,)).fetchone()
            if not user or user["status"] != "active":
                raise ValueError("user is missing or inactive")
            if source_id:
                existing = db.execute("""SELECT id FROM entitlement_events
                    WHERE user_id=? AND event_type=? AND source_id=?""",
                    (user_id, source, source_id)).fetchone()
                if existing:
                    return existing["id"]
            row = db.execute("""SELECT MAX(expires_at) AS expiry FROM subscriptions
                WHERE user_id=? AND status='active' AND expires_at>?""",
                (user_id, now)).fetchone()
            starts_at = max(now, int(row["expiry"] or now))
            expires_at = starts_at + int(duration_seconds)
            db.execute("""INSERT INTO subscriptions
                (id,user_id,plan,starts_at,expires_at,source,status,created_at)
                VALUES (?,?,?,?,?,?, 'active',?)""",
                (sub_id,user_id,plan,starts_at,expires_at,source,now))
            db.execute("""INSERT INTO entitlement_events
                (id,user_id,event_type,source_id,starts_at,expires_at,created_at)
                VALUES (?,?,?,?,?,?,?)""",
                (event_id,user_id,source,source_id,starts_at,expires_at,now))
            return sub_id

    def create_referral(self, inviter_user_id: str, invited_user_id: str, code: str) -> str:
        """Create a pending referral; qualification/rewards are separate steps."""
        referral_id = secrets.token_urlsafe(18)
        with self.connection() as db:
            owner = db.execute("SELECT user_id FROM referral_codes WHERE code=?",
                               (code.upper(),)).fetchone()
            if not owner or owner["user_id"] != inviter_user_id:
                raise ValueError("invalid referral code")
            if inviter_user_id == invited_user_id:
                raise ValueError("self-referral is not allowed")
            db.execute("""INSERT INTO referrals
                (id,inviter_user_id,invited_user_id,code,status,created_at)
                VALUES (?,?,?,?, 'pending',?)""",
                (referral_id,inviter_user_id,invited_user_id,code.upper(),_now()))
            return referral_id
