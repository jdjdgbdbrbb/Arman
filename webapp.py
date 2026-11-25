import time, hmac, hashlib
from urllib.parse import parse_qsl
from flask import Flask, jsonify, request, render_template
from config import BOT_TOKEN, CURRENCY_LABEL
from db import db, init_db

app = Flask(__name__)
init_db()

def telegram_user():
    """Verify Telegram Mini App initData; never trust a user_id supplied by browser."""
    raw = request.headers.get("X-Telegram-Init-Data", "")
    if not raw or not BOT_TOKEN:
        return None
    data = dict(parse_qsl(raw, keep_blank_values=True))
    received_hash = data.pop("hash", None)
    if not received_hash:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        return None
    import json
    try:
        return json.loads(data["user"])
    except Exception:
        return None

def require_user():
    u = telegram_user()
    if not u or not u.get("id"):
        return None
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id,username) VALUES(?,?)",
                  (int(u["id"]), u.get("username", "")))
    return int(u["id"])

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/videos")
def videos():
    uid = require_user()
    if not uid:
        return jsonify(error="Telegram থেকে Web App খুলুন।"), 401
    with db() as c:
        rows = c.execute("""
            SELECT v.id,v.title,v.url,v.reward,v.min_seconds,
            CASE WHEN cl.id IS NULL THEN 0 ELSE 1 END claimed
            FROM videos v LEFT JOIN video_claims cl
            ON cl.video_id=v.id AND cl.user_id=?
            WHERE v.active=1 ORDER BY v.id DESC
        """, (uid,)).fetchall()
    return jsonify(videos=[dict(r) for r in rows])

@app.get("/api/balance")
def get_balance():
    uid = require_user()
    if not uid:
        return jsonify(error="Unauthorized"), 401
    with db() as c:
        row = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
    return jsonify(balance=float(row["balance"]) if row else 0, currency=CURRENCY_LABEL)

@app.post("/api/start/<int:video_id>")
def start_video(video_id):
    uid = require_user()
    if not uid:
        return jsonify(error="Unauthorized"), 401
    with db() as c:
        video = c.execute("SELECT id FROM videos WHERE id=? AND active=1", (video_id,)).fetchone()
        if not video:
            return jsonify(error="ভিডিও পাওয়া যায়নি"), 404
        if c.execute("SELECT 1 FROM video_claims WHERE user_id=? AND video_id=?", (uid, video_id)).fetchone():
            return jsonify(error="আগেই Claim করা হয়েছে"), 409
        c.execute("""INSERT INTO watch_sessions(user_id,video_id,started_at) VALUES(?,?,?)
                     ON CONFLICT(user_id,video_id) DO UPDATE SET started_at=excluded.started_at""",
                  (uid, video_id, time.time()))
    return jsonify(ok=True)

@app.post("/api/claim/<int:video_id>")
def claim_video(video_id):
    uid = require_user()
    if not uid:
        return jsonify(error="Unauthorized"), 401
    with db() as c:
        v = c.execute("SELECT reward,min_seconds FROM videos WHERE id=? AND active=1", (video_id,)).fetchone()
        s = c.execute("SELECT started_at FROM watch_sessions WHERE user_id=? AND video_id=?",
                      (uid, video_id)).fetchone()
        if not v or not s:
            return jsonify(error="আগে ভিডিও Start করুন"), 400
        if time.time() - s["started_at"] < v["min_seconds"]:
            return jsonify(error=f"কমপক্ষে {v['min_seconds']} সেকেন্ড অপেক্ষা করুন"), 400
        try:
            c.execute("INSERT INTO video_claims(user_id,video_id) VALUES(?,?)", (uid, video_id))
        except Exception:
            return jsonify(error="এই ভিডিওর Reward আগে নেওয়া হয়েছে"), 409
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (v["reward"], uid))
        c.execute("DELETE FROM watch_sessions WHERE user_id=? AND video_id=?", (uid, video_id))
    return jsonify(ok=True, reward=float(v["reward"]))


@app.get("/ads_config.js")
def ads_config():
    from flask import Response
    from ads import ADS_ENABLED, AD_PROVIDER, AD_CLIENT_ID, AD_SLOT_ID, AD_SCRIPT_URL
    import json
    payload = {
        "enabled": ADS_ENABLED, "provider": AD_PROVIDER,
        "clientId": AD_CLIENT_ID, "slotId": AD_SLOT_ID, "scriptUrl": AD_SCRIPT_URL
    }
    return Response("window.ARMAN_ADS = " + json.dumps(payload) + ";", mimetype="application/javascript")
