import os
import logging
import sqlite3
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# Paste your BotFather token into BOT_TOKEN below, or set it as an environment variable.
BOT_TOKEN = os.getenv("9204996076:AAHK8KiYEiK0_gh2bhvzyN6M4eNaovRwB9s", "9204996076:AAHK8KiYEiK0_gh2bhvzyN6M4eNaovRwB9s").strip()
ADMIN_ID = int(os.getenv("@ItsArman36", "0"))  #@ItsArman36
DB_PATH = os.getenv("DB_PATH", "first_bot.db")
REFERRAL_REWARD = int(os.getenv("REFERRAL_REWARD", "10"))
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "100"))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("first-bot")

MENU = ReplyKeyboardMarkup(
    [["💰 Balance", "📋 Tasks"], ["👥 Referral", "💸 Withdraw"], ["ℹ️ Help"]],
    resize_keyboard=True
)

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def now():
    return datetime.now(timezone.utc).isoformat()

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER NOT NULL DEFAULT 0,
            referred_by INTEGER, joined_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks(
            task_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            points INTEGER NOT NULL, url TEXT, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS submissions(
            submission_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL, proof TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS withdrawals(
            withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL, method TEXT NOT NULL, details TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL
        );
        """)

def user_row(uid):
    with connect() as con:
        return con.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if not user_row(u.id):
        referrer = None
        if context.args:
            try:
                candidate = int(context.args[0])
                if candidate != u.id and user_row(candidate):
                    referrer = candidate
            except ValueError:
                pass
        with connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO users(user_id,username,referred_by,joined_at) VALUES(?,?,?,?)",
                (u.id, u.username or "", referrer, now())
            )
            if referrer:
                con.execute("UPDATE users SET balance=balance+? WHERE user_id=?",
                            (REFERRAL_REWARD, referrer))
        if referrer:
            try:
                await context.bot.send_message(
                    referrer, f"🎉 নতুন রেফারেল! +{REFERRAL_REWARD} পয়েন্ট যোগ হয়েছে।"
                )
            except Exception:
                log.exception("Referral notification failed")
    await update.message.reply_text(
        f"স্বাগতম {u.first_name}!\\nFirst bot-এ টাস্ক করে পয়েন্ট সংগ্রহ করুন।",
        reply_markup=MENU
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = user_row(update.effective_user.id)
    await update.message.reply_text(
        f"💰 আপনার ব্যালেন্স: {row['balance'] if row else 0} পয়েন্ট",
        reply_markup=MENU
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start={update.effective_user.id}"
    await update.message.reply_text(
        f"👥 আপনার রেফারেল লিংক:\\n{link}\\nনতুন ইউজার যোগ হলে {REFERRAL_REWARD} পয়েন্ট পাবেন।",
        reply_markup=MENU
    )

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with connect() as con:
        rows = con.execute("SELECT * FROM tasks WHERE active=1 ORDER BY task_id").fetchall()
    if not rows:
        await update.message.reply_text("এখনো কোনো টাস্ক যোগ করা হয়নি।", reply_markup=MENU)
        return
    out = ["📋 টাস্কসমূহ:"]
    for t in rows:
        out.append(f"\\n#{t['task_id']} — {t['title']} ({t['points']} পয়েন্ট)")
        if t["url"]:
            out.append(t["url"])
        out.append(f"প্রমাণ জমা: /submit {t['task_id']} আপনার_প্রমাণ")
    await update.message.reply_text("\\n".join(out), reply_markup=MENU)

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("ব্যবহার: /submit TASK_ID প্রমাণ_বা_লিংক")
        return
    try:
        tid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("সঠিক Task ID দিন।")
        return
    proof = " ".join(context.args[1:])
    with connect() as con:
        task = con.execute("SELECT * FROM tasks WHERE task_id=? AND active=1", (tid,)).fetchone()
        if not task:
            await update.message.reply_text("টাস্ক পাওয়া যায়নি বা বন্ধ আছে।")
            return
        old = con.execute(
            "SELECT 1 FROM submissions WHERE user_id=? AND task_id=? AND status IN ('pending','approved')",
            (update.effective_user.id, tid)
        ).fetchone()
        if old:
            await update.message.reply_text("এই টাস্কের আবেদন আগে জমা হয়েছে।")
            return
        cur = con.execute(
            "INSERT INTO submissions(user_id,task_id,proof,created_at) VALUES(?,?,?,?)",
            (update.effective_user.id, tid, proof, now())
        )
        sid = cur.lastrowid
    if ADMIN_ID:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("Approve", callback_data=f"sub:yes:{sid}"),
            InlineKeyboardButton("Reject", callback_data=f"sub:no:{sid}")
        ]])
        await context.bot.send_message(
            ADMIN_ID, f"Task submission #{sid}\\nUser: {update.effective_user.id}\\nTask: {tid}\\nProof: {proof}",
            reply_markup=kb
        )
    await update.message.reply_text("✅ প্রমাণ জমা হয়েছে। অ্যাডমিন যাচাই করবেন।", reply_markup=MENU)

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            f"ব্যবহার: /withdraw POINTS METHOD ACCOUNT_DETAILS\\nসর্বনিম্ন {MIN_WITHDRAW} পয়েন্ট"
        )
        return
    try:
        amount = int(context.args[0])
    except ValueError:
        await update.message.reply_text("পয়েন্ট সংখ্যায় লিখুন।")
        return
    method, details = context.args[1], " ".join(context.args[2:])
    if amount < MIN_WITHDRAW:
        await update.message.reply_text(f"সর্বনিম্ন {MIN_WITHDRAW} পয়েন্ট।")
        return
    with connect() as con:
        row = con.execute("SELECT balance FROM users WHERE user_id=?",
                          (update.effective_user.id,)).fetchone()
        if not row or row["balance"] < amount:
            await update.message.reply_text("আপনার পর্যাপ্ত ব্যালেন্স নেই।")
            return
        con.execute("UPDATE users SET balance=balance-? WHERE user_id=?",
                    (amount, update.effective_user.id))
        cur = con.execute(
            "INSERT INTO withdrawals(user_id,amount,method,details,created_at) VALUES(?,?,?,?,?)",
            (update.effective_user.id, amount, method, details, now())
        )
        wid = cur.lastrowid
    if ADMIN_ID:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("Mark paid", callback_data=f"wd:yes:{wid}"),
            InlineKeyboardButton("Reject + refund", callback_data=f"wd:no:{wid}")
        ]])
        await context.bot.send_message(
            ADMIN_ID, f"Withdrawal #{wid}\\nUser: {update.effective_user.id}\\nAmount: {amount}\\nMethod: {method}\\nDetails: {details}",
            reply_markup=kb
        )
    await update.message.reply_text("✅ Withdraw আবেদন জমা হয়েছে।", reply_markup=MENU)

async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    raw = " ".join(context.args)
    parts = [x.strip() for x in raw.split("|")]
    if len(parts) != 3:
        await update.message.reply_text("ফরম্যাট: /addtask টাস্কের নাম | পয়েন্ট | URL")
        return
    try:
        points = int(parts[1])
        if points <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("পয়েন্ট অবশ্যই ধনাত্মক সংখ্যা হতে হবে।")
        return
    with connect() as con:
        cur = con.execute("INSERT INTO tasks(title,points,url) VALUES(?,?,?)",
                          (parts[0], points, parts[2]))
    await update.message.reply_text(f"✅ Task #{cur.lastrowid} যোগ হয়েছে।")

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not ADMIN_ID or q.from_user.id != ADMIN_ID:
        await q.edit_message_text("অনুমতি নেই।")
        return
    try:
        kind, decision, item = q.data.split(":")
        item = int(item)
    except Exception:
        await q.edit_message_text("ভুল অ্যাকশন।")
        return
    with connect() as con:
        if kind == "sub":
            row = con.execute(
                "SELECT s.*,t.points FROM submissions s JOIN tasks t ON t.task_id=s.task_id WHERE s.submission_id=?",
                (item,)
            ).fetchone()
            if not row or row["status"] != "pending":
                await q.edit_message_text("আবেদনটি পাওয়া যায়নি বা আগে দেখা হয়েছে।")
                return
            status = "approved" if decision == "yes" else "rejected"
            con.execute("UPDATE submissions SET status=? WHERE submission_id=?", (status, item))
            if decision == "yes":
                con.execute("UPDATE users SET balance=balance+? WHERE user_id=?",
                            (row["points"], row["user_id"]))
                msg = f"আপনার টাস্ক অনুমোদিত। +{row['points']} পয়েন্ট পেয়েছেন।"
            else:
                msg = "আপনার টাস্ক আবেদনটি গ্রহণ করা হয়নি।"
            await context.bot.send_message(row["user_id"], msg)
            await q.edit_message_text(f"Submission #{item}: {status}")
        elif kind == "wd":
            row = con.execute("SELECT * FROM withdrawals WHERE withdrawal_id=?", (item,)).fetchone()
            if not row or row["status"] != "pending":
                await q.edit_message_text("আবেদনটি পাওয়া যায়নি বা আগে প্রসেস হয়েছে।")
                return
            if decision == "yes":
                con.execute("UPDATE withdrawals SET status='paid' WHERE withdrawal_id=?", (item,))
                msg, status = "আপনার Withdraw পেমেন্ট সম্পন্ন হয়েছে।", "paid"
            else:
                con.execute("UPDATE withdrawals SET status='rejected' WHERE withdrawal_id=?", (item,))
                con.execute("UPDATE users SET balance=balance+? WHERE user_id=?",
                            (row["amount"], row["user_id"]))
                msg, status = f"Withdraw বাতিল। {row['amount']} পয়েন্ট ফেরত দেওয়া হয়েছে।", "refunded"
            await context.bot.send_message(row["user_id"], msg)
            await q.edit_message_text(f"Withdrawal #{item}: {status}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "কমান্ড:\\n/start\\n/balance\\n/tasks\\n/submit TASK_ID PROOF\\n/referral\\n/withdraw POINTS METHOD DETAILS\\n/addtask TITLE | POINTS | URL (admin)",
        reply_markup=MENU
    )

async def menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "💰 Balance":
        await balance(update, context)
    elif choice == "📋 Tasks":
        await tasks(update, context)
    elif choice == "👥 Referral":
        await referral(update, context)
    elif choice == "💸 Withdraw":
        await update.message.reply_text(
            f"/withdraw POINTS METHOD ACCOUNT_DETAILS\\nসর্বনিম্ন {MIN_WITHDRAW} পয়েন্ট"
        )
    elif choice == "ℹ️ Help":
        await help_cmd(update, context)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN খালি আছে। bot.py-তে BOT_TOKEN বসান অথবা environment variable দিন।")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("addtask", addtask))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(admin_action))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_text))
    log.info("First bot is running.")
    app.run_polling()

if __name__ == "__main__":
    main()
