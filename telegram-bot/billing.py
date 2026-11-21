"""SQLite billing and clip-quota service for the ARIA Telegram bot.

All timestamps are UTC ISO-8601. Weekly and monthly clip plans are separate
from the bot's free chat/search quotas.
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DB_PATH = "/app/data/aria.sqlite3"
TEHRAN = ZoneInfo("Asia/Tehran")

PLANS = {
    "weekly": {
        "title": "هفتگی",
        "amount": 600_000,
        "days": 7,
        "clips": 28,
        "daily_limit": 4,
    },
    "monthly": {
        "title": "ماهانه",
        "amount": 2_400_000,
        "days": 30,
        "clips": 140,
        "daily_limit": None,
    },
}


def now_utc():
    return datetime.now(timezone.utc)


def to_iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_dt(value):
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def today_tehran(value=None):
    return (value or now_utc()).astimezone(TEHRAN).date().isoformat()


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=20000")
    return conn


def init_db():
    conn = connect()
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS clip_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_key TEXT NOT NULL,
            amount INTEGER NOT NULL,
            receipt_file_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','approved','rejected')),
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by INTEGER,
            review_note TEXT,
            subscription_id INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_clip_payments_user_status
            ON clip_payments(user_id, status);

        CREATE TABLE IF NOT EXISTS clip_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            payment_id INTEGER NOT NULL UNIQUE,
            plan_key TEXT NOT NULL,
            starts_at TEXT NOT NULL,
            ends_at TEXT NOT NULL,
            total_clips INTEGER NOT NULL,
            used_clips INTEGER NOT NULL DEFAULT 0,
            daily_limit INTEGER,
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active','queued','expired')),
            created_at TEXT NOT NULL,
            FOREIGN KEY(payment_id) REFERENCES clip_payments(id)
        );

        CREATE INDEX IF NOT EXISTS idx_clip_subscriptions_user_dates
            ON clip_subscriptions(user_id, starts_at, ends_at);

        CREATE TABLE IF NOT EXISTS clip_daily_usage (
            subscription_id INTEGER NOT NULL,
            usage_date TEXT NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(subscription_id, usage_date),
            FOREIGN KEY(subscription_id) REFERENCES clip_subscriptions(id)
        );

        CREATE TABLE IF NOT EXISTS clip_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'reserved'
                CHECK(status IN ('reserved','completed','failed')),
            FOREIGN KEY(subscription_id) REFERENCES clip_subscriptions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_clip_jobs_status
            ON clip_jobs(status);
        """)
        conn.commit()
    finally:
        conn.close()


def create_payment(user_id, plan_key, receipt_file_id):
    if plan_key not in PLANS:
        raise ValueError("پلن نامعتبر است.")
    if not receipt_file_id:
        raise ValueError("شناسه رسید خالی است.")

    plan = PLANS[plan_key]
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        pending = conn.execute(
            "SELECT id FROM clip_payments WHERE user_id=? AND status='pending'",
            (user_id,),
        ).fetchone()
        if pending:
            conn.rollback()
            raise ValueError("برای شما یک درخواست پرداخت در انتظار بررسی وجود دارد.")

        cur = conn.execute(
            """INSERT INTO clip_payments
               (user_id, plan_key, amount, receipt_file_id, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, plan_key, plan["amount"], receipt_file_id, to_iso(now_utc())),
        )
        payment_id = cur.lastrowid
        conn.commit()
        return payment_id
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def get_payment(payment_id):
    conn = connect()
    try:
        return conn.execute(
            "SELECT * FROM clip_payments WHERE id=?", (payment_id,)
        ).fetchone()
    finally:
        conn.close()


def list_pending_payments(limit=20):
    conn = connect()
    try:
        return conn.execute(
            """SELECT * FROM clip_payments WHERE status='pending'
               ORDER BY created_at ASC LIMIT ?""",
            (max(1, min(int(limit), 100)),),
        ).fetchall()
    finally:
        conn.close()


def approve_payment(payment_id, admin_id):
    """Approve once and queue the subscription after all existing paid periods."""
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        payment = conn.execute(
            "SELECT * FROM clip_payments WHERE id=?", (payment_id,)
        ).fetchone()
        if not payment or payment["status"] != "pending":
            conn.rollback()
            return None

        plan = PLANS.get(payment["plan_key"])
        if not plan or payment["amount"] != plan["amount"]:
            conn.rollback()
            raise ValueError("مبلغ یا پلن درخواست پرداخت با تنظیمات معتبر مطابقت ندارد.")

        now = now_utc()
        latest = conn.execute(
            """SELECT MAX(ends_at) AS latest_end FROM clip_subscriptions
               WHERE user_id=? AND ends_at>? AND status IN ('active','queued')""",
            (payment["user_id"], to_iso(now)),
        ).fetchone()["latest_end"]

        start = max(now, parse_dt(latest)) if latest else now
        end = start + timedelta(days=plan["days"])
        status = "queued" if start > now else "active"

        cur = conn.execute(
            """INSERT INTO clip_subscriptions
               (user_id, payment_id, plan_key, starts_at, ends_at,
                total_clips, daily_limit, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payment["user_id"], payment_id, payment["plan_key"],
                to_iso(start), to_iso(end), plan["clips"],
                plan["daily_limit"], status, to_iso(now),
            ),
        )
        subscription_id = cur.lastrowid
        conn.execute(
            """UPDATE clip_payments SET status='approved', reviewed_at=?,
               reviewed_by=?, subscription_id=? WHERE id=? AND status='pending'""",
            (to_iso(now), admin_id, subscription_id, payment_id),
        )
        conn.commit()
        return {
            "subscription_id": subscription_id,
            "user_id": payment["user_id"],
            "plan_key": payment["plan_key"],
            "starts_at": to_iso(start),
            "ends_at": to_iso(end),
            "queued": status == "queued",
            "clips": plan["clips"],
        }
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def reject_payment(payment_id, admin_id, note=""):
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            """UPDATE clip_payments SET status='rejected', reviewed_at=?,
               reviewed_by=?, review_note=?
               WHERE id=? AND status='pending'""",
            (to_iso(now_utc()), admin_id, (note or "")[:500], payment_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def get_account(user_id):
    now = now_utc()
    conn = connect()
    try:
        active = conn.execute(
            """SELECT * FROM clip_subscriptions
               WHERE user_id=? AND status='active' AND starts_at<=? AND ends_at>?
               ORDER BY ends_at DESC LIMIT 1""",
            (user_id, to_iso(now), to_iso(now)),
        ).fetchone()
        queued = conn.execute(
            """SELECT * FROM clip_subscriptions
               WHERE user_id=? AND status IN ('active','queued') AND starts_at>?
               ORDER BY starts_at ASC""",
            (user_id, to_iso(now)),
        ).fetchall()
        pending = conn.execute(
            """SELECT id, plan_key, amount, created_at FROM clip_payments
               WHERE user_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
        return {"active": active, "queued": queued, "pending": pending}
    finally:
        conn.close()


def reserve_clip(user_id):
    """Reserve one clip atomically. Failed jobs must call finish_clip(..., False)."""
    now = now_utc()
    date_key = today_tehran(now)
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        sub = conn.execute(
            """SELECT * FROM clip_subscriptions
               WHERE user_id=? AND status IN ('active','queued')
                 AND starts_at<=? AND ends_at>?
               ORDER BY ends_at DESC LIMIT 1""",
            (user_id, to_iso(now), to_iso(now)),
        ).fetchone()

        if not sub:
            conn.rollback()
            return {"ok": False, "reason": "no_active_subscription"}

        if sub["used_clips"] >= sub["total_clips"]:
            conn.rollback()
            return {"ok": False, "reason": "total_quota_exhausted"}

        usage = conn.execute(
            """SELECT used FROM clip_daily_usage
               WHERE subscription_id=? AND usage_date=?""",
            (sub["id"], date_key),
        ).fetchone()
        used_today = usage["used"] if usage else 0
        if sub["daily_limit"] is not None and used_today >= sub["daily_limit"]:
            conn.rollback()
            return {"ok": False, "reason": "daily_quota_exhausted"}

        conn.execute(
            "UPDATE clip_subscriptions SET used_clips=used_clips+1 WHERE id=?",
            (sub["id"],),
        )
        conn.execute(
            """INSERT INTO clip_daily_usage(subscription_id, usage_date, used)
               VALUES (?, ?, 1)
               ON CONFLICT(subscription_id, usage_date)
               DO UPDATE SET used=used+1""",
            (sub["id"], date_key),
        )
        cur = conn.execute(
            """INSERT INTO clip_jobs(user_id, subscription_id, created_at)
               VALUES (?, ?, ?)""",
            (user_id, sub["id"], to_iso(now)),
        )
        conn.commit()
        return {
            "ok": True,
            "job_id": cur.lastrowid,
            "subscription_id": sub["id"],
            "remaining": sub["total_clips"] - sub["used_clips"] - 1,
            "daily_remaining": (
                None if sub["daily_limit"] is None
                else sub["daily_limit"] - used_today - 1
            ),
        }
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def finish_clip(job_id, success):
    """Complete a reserved job or refund both total and original Tehran-day quota."""
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        job = conn.execute(
            "SELECT * FROM clip_jobs WHERE id=?", (job_id,)
        ).fetchone()
        if not job or job["status"] != "reserved":
            conn.rollback()
            return False

        new_status = "completed" if success else "failed"
        conn.execute(
            "UPDATE clip_jobs SET status=? WHERE id=? AND status='reserved'",
            (new_status, job_id),
        )
        if not success:
            job_date = today_tehran(parse_dt(job["created_at"]))
            conn.execute(
                """UPDATE clip_subscriptions
                   SET used_clips=CASE WHEN used_clips>0 THEN used_clips-1 ELSE 0 END
                   WHERE id=?""",
                (job["subscription_id"],),
            )
            conn.execute(
                """UPDATE clip_daily_usage
                   SET used=CASE WHEN used>0 THEN used-1 ELSE 0 END
                   WHERE subscription_id=? AND usage_date=?""",
                (job["subscription_id"], job_date),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def recover_abandoned_jobs():
    """Refund reservations left behind by a process restart."""
    conn = connect()
    try:
        ids = [
            row["id"] for row in conn.execute(
                "SELECT id FROM clip_jobs WHERE status='reserved'"
            ).fetchall()
        ]
    finally:
        conn.close()

    recovered = 0
    for job_id in ids:
        if finish_clip(job_id, False):
            recovered += 1
    return recovered
