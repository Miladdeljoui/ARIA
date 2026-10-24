"""First public ARIA API milestone.

Run with: python -m server.public_api
Required env: ARIA_GOOGLE_CLIENT_ID, ARIA_SESSION_SECRET, ARIA_OWNER_GOOGLE_SUB.
Optional env: ARIA_PUBLIC_DB, ARIA_PORT.
Place behind HTTPS before public deployment. Payment gateway verification and admin
web UI are deliberately not simulated here.
"""
from __future__ import annotations
import hmac
import os
import secrets
import time
from functools import wraps

import requests
from flask import Flask, g, jsonify, request, session
from server.public_store import PublicStore

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("ARIA_SESSION_SECRET", ""),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("ARIA_COOKIE_SECURE", "1") == "1",
    MAX_CONTENT_LENGTH=256 * 1024,
)
store = PublicStore()
TRIAL_SECONDS = 3 * 24 * 60 * 60
REFERRAL_SECONDS = 2 * 24 * 60 * 60


def require_config():
    if not app.config["SECRET_KEY"] or len(app.config["SECRET_KEY"]) < 32:
        return "ARIA_SESSION_SECRET must be a random secret of at least 32 characters"
    if not os.environ.get("ARIA_GOOGLE_CLIENT_ID"):
        return "ARIA_GOOGLE_CLIENT_ID is not configured"
    return None


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with store.connection() as db:
        row = db.execute(
            "SELECT id,email,email_verified,display_name,role,status,created_at "
            "FROM public_users WHERE id=?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user["status"] != "active":
            return jsonify(error="authentication_required"), 401
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


def owner_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user["status"] != "active" or user["role"] != "owner":
            return jsonify(error="owner_only"), 403
        g.user = user
        return fn(*args, **kwargs)
    return wrapper


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return jsonify(service="ARIA Public API", status="ok", configured=not require_config())


@app.post("/api/auth/google")
def google_login():
    config_error = require_config()
    if config_error:
        return jsonify(error="server_not_configured", detail=config_error), 503
    body = request.get_json(silent=True) or {}
    credential = body.get("credential")
    if not isinstance(credential, str) or not credential or len(credential) > 10000:
        return jsonify(error="missing_google_credential"), 400
    try:
        resp = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": credential}, timeout=8,
        )
        if not resp.ok:
            return jsonify(error="invalid_google_credential"), 401
        claims = resp.json()
    except requests.RequestException:
        return jsonify(error="identity_provider_unavailable"), 503
    expected_aud = os.environ["ARIA_GOOGLE_CLIENT_ID"]
    if not hmac.compare_digest(str(claims.get("aud", "")), expected_aud):
        return jsonify(error="wrong_token_audience"), 401
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return jsonify(error="wrong_token_issuer"), 401
    try:
        if int(claims.get("exp", "0")) <= int(time.time()):
            return jsonify(error="expired_google_credential"), 401
    except (TypeError, ValueError):
        return jsonify(error="invalid_google_expiry"), 401
    subject = claims.get("sub")
    email = claims.get("email", "")
    verified = claims.get("email_verified") in (True, "true", "True")
    if not subject or not email or not verified:
        return jsonify(error="verified_google_email_required"), 401

    user_id, created = store.create_user(
        str(subject), str(email), True, str(claims.get("name", ""))[:160]
    )
    owner_sub = os.environ.get("ARIA_OWNER_GOOGLE_SUB", "")
    if owner_sub and hmac.compare_digest(str(subject), owner_sub):
        with store.connection() as db:
            db.execute("UPDATE public_users SET role='owner',updated_at=? WHERE id=?",
                       (int(time.time()), user_id))
    session.clear()
    session["user_id"] = user_id
    session["csrf"] = secrets.token_urlsafe(24)
    if created:
        try:
            store.grant_subscription(user_id, "trial", TRIAL_SECONDS, "trial",
                                     source_id="first-trial", now=int(time.time()))
        except Exception:
            app.logger.exception("Could not create initial trial")
    code = store.ensure_referral_code(user_id)
    return jsonify(ok=True, created=created, user=current_user(),
                   referral_code=code, csrf_token=session["csrf"])


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.get("/api/me")
@login_required
def me():
    user = g.user
    code = store.ensure_referral_code(user["id"])
    with store.connection() as db:
        subscriptions = [dict(row) for row in db.execute(
            "SELECT plan,starts_at,expires_at,source,status FROM subscriptions "
            "WHERE user_id=? ORDER BY starts_at DESC LIMIT 30", (user["id"],)
        ).fetchall()]
        referrals = [dict(row) for row in db.execute(
            "SELECT status,created_at,qualified_at FROM referrals "
            "WHERE inviter_user_id=? ORDER BY created_at DESC LIMIT 100", (user["id"],)
        ).fetchall()]
    return jsonify(user=user, referral_code=code,
                   pro_active=store.has_active_pro(user["id"]),
                   subscriptions=subscriptions, referrals=referrals,
                   trial_days=3, referral_reward_days=2)


@app.post("/api/referrals/redeem")
@login_required
def redeem_referral():
    body = request.get_json(silent=True) or {}
    code = str(body.get("code", "")).strip().upper()
    if not code or len(code) > 32:
        return jsonify(error="invalid_referral_code"), 400
    if not g.user.get("id"):
        return jsonify(error="authentication_required"), 401
    with store.connection() as db:
        row = db.execute("SELECT user_id FROM referral_codes WHERE code=?", (code,)).fetchone()
    if not row:
        return jsonify(error="invalid_referral_code"), 400
    if row["user_id"] == g.user["id"]:
        return jsonify(error="self_referral_not_allowed"), 400
    # A referral must be linked to a newly created account, before any reward.
    with store.connection() as db:
        prior = db.execute("SELECT id FROM referrals WHERE invited_user_id=?",
                           (g.user["id"],)).fetchone()
        created = db.execute("SELECT created_at FROM public_users WHERE id=?",
                             (g.user["id"],)).fetchone()
    if prior:
        return jsonify(error="referral_already_used"), 409
    if not created or int(time.time()) - int(created["created_at"]) > 24 * 60 * 60:
        return jsonify(error="referral_window_expired"), 409
    try:
        rid = store.create_referral(row["user_id"], g.user["id"], code)
    except ValueError:
        return jsonify(error="invalid_referral_code"), 400
    return jsonify(ok=True, referral_id=rid, status="pending",
                   message="پاداش پس از تکمیل شرایط دعوت تأیید می‌شود."), 201


@app.get("/api/subscription")
@login_required
def subscription_status():
    return jsonify(pro_active=store.has_active_pro(g.user["id"]),
                   owner_access=(g.user["role"] == "owner"))


@app.post("/api/orders")
@login_required
def create_order():
    body = request.get_json(silent=True) or {}
    plan = body.get("plan")
    method = body.get("method")
    amount = body.get("amount_minor")
    currency = str(body.get("currency", "IRR"))[:8]
    if plan not in ("pro", "pro_plus") or method not in ("gateway", "bank_transfer"):
        return jsonify(error="invalid_order"), 400
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return jsonify(error="invalid_amount"), 400
    if amount <= 0 or amount > 10**12:
        return jsonify(error="invalid_amount"), 400
    order_id = secrets.token_urlsafe(18)
    now = int(time.time())
    with store.connection() as db:
        db.execute("""INSERT INTO orders
            (id,user_id,plan,amount_minor,currency,method,status,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?, ?,?)""",
            (order_id,g.user["id"],plan,amount,currency,method,
             "pending_review" if method == "bank_transfer" else "pending",now,now))
    # Gateway orders are only pending records. Never mark paid without verified provider callback.
    return jsonify(order_id=order_id,
                   status="pending_review" if method == "bank_transfer" else "pending",
                   message="درگاه تا زمان اتصال و اعتبارسنجی callback فعال نیست."), 201


@app.get("/api/admin/overview")
@owner_required
def admin_overview():
    with store.connection() as db:
        counts = {
            "users": db.execute("SELECT COUNT(*) FROM public_users").fetchone()[0],
            "active_users": db.execute("SELECT COUNT(*) FROM public_users WHERE status='active'").fetchone()[0],
            "pending_orders": db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('pending','pending_review')").fetchone()[0],
            "qualified_referrals": db.execute("SELECT COUNT(*) FROM referrals WHERE status='qualified'").fetchone()[0],
        }
        orders = [dict(row) for row in db.execute(
            "SELECT id,user_id,plan,amount_minor,currency,method,status,created_at "
            "FROM orders ORDER BY created_at DESC LIMIT 100").fetchall()]
    return jsonify(counts=counts, recent_orders=orders)


@app.post("/api/admin/orders/<order_id>/review")
@owner_required
def review_order(order_id):
    body = request.get_json(silent=True) or {}
    action = body.get("action")
    note = str(body.get("note", ""))[:500]
    if action not in ("approve", "reject"):
        return jsonify(error="action_must_be_approve_or_reject"), 400
    now = int(time.time())
    with store.connection() as db:
        order = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            return jsonify(error="order_not_found"), 404
        if order["method"] != "bank_transfer" or order["status"] != "pending_review":
            return jsonify(error="order_not_reviewable"), 409
        status = "paid" if action == "approve" else "rejected"
        db.execute("""UPDATE orders SET status=?,admin_note=?,reviewed_by=?,reviewed_at=?,updated_at=?
            WHERE id=? AND status='pending_review'""",
            (status,note,g.user["id"],now,now,order_id))
    if action == "approve":
        # Idempotent source_id ensures retrying the review cannot double-grant.
        store.grant_subscription(order["user_id"], order["plan"], 30*86400,
                                 "manual_payment", source_id=order_id, now=now)
    with store.connection() as db:
        db.execute("""INSERT INTO audit_log
            (id,actor_user_id,action,target_type,target_id,details_json,created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (secrets.token_urlsafe(18),g.user["id"],"order_"+action,"order",order_id,
             "{}",now))
    return jsonify(ok=True, order_id=order_id, status=status)


@app.post("/api/admin/referrals/<referral_id>/qualify")
@owner_required
def qualify_referral(referral_id):
    now = int(time.time())
    with store.connection() as db:
        referral = db.execute("SELECT * FROM referrals WHERE id=?", (referral_id,)).fetchone()
        if not referral:
            return jsonify(error="referral_not_found"), 404
        if referral["status"] != "pending":
            return jsonify(error="referral_not_pending"), 409
        db.execute("UPDATE referrals SET status='qualified',qualified_at=? WHERE id=? AND status='pending'",
                   (now, referral_id))
    # Idempotency keys ensure retrying cannot duplicate either user's reward.
    store.grant_subscription(referral["inviter_user_id"], "pro", REFERRAL_SECONDS,
                             "referral", source_id=referral_id+":inviter", now=now)
    store.grant_subscription(referral["invited_user_id"], "pro", REFERRAL_SECONDS,
                             "referral", source_id=referral_id+":invitee", now=now)
    with store.connection() as db:
        db.execute("""INSERT INTO audit_log
            (id,actor_user_id,action,target_type,target_id,details_json,created_at)
            VALUES (?,?,?,?,?,?,?)""",
            (secrets.token_urlsafe(18),g.user["id"],"referral_qualify","referral",referral_id,"{}",now))
    return jsonify(ok=True, referral_id=referral_id, reward_days_each=2)


if __name__ == "__main__":
    if not app.config["SECRET_KEY"]:
        raise SystemExit("Set ARIA_SESSION_SECRET to a random value of at least 32 characters.")
    app.run(host="127.0.0.1", port=int(os.getenv("ARIA_PUBLIC_PORT", "8787")), debug=False)
