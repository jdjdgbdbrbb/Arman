import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from config import *
from db import db, init_db

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("arman")

def ensure_user(u):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)",
                  (u.id, u.username or ""))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ensure_user(u)
    keyboard = []
    if WEBAPP_URL.startswith("https://") and "YOUR-APP-DOMAIN" not in WEBAPP_URL:
        keyboard.append([InlineKeyboardButton("🎬 ভিডিও দেখে আয়", web_app=WebAppInfo(url=WEBAPP_URL))])
    keyboard.append([InlineKeyboardButton("📢 গ্রুপে Join করুন", url=GROUP_LINK)])
    keyboard.append([InlineKeyboardButton("✅ Join Reward Claim (২ টাকা)", callback_data="claim_group")])
    await update.message.reply_text(
        f"স্বাগতম {u.first_name}!\nভিডিও, রেফারেল ও টাস্ক থেকে রিওয়ার্ড সংগ্রহ করুন।\n\n"
        "কমান্ড: /balance /withdraw /vip /help",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    with db() as c:
        row = c.execute("SELECT balance,vip_until FROM users WHERE user_id=?",
                        (update.effective_user.id,)).fetchone()
    await update.message.reply_text(f"💰 ব্যালেন্স: {row['balance']:.2f} {CURRENCY_LABEL}\nVIP: {row['vip_until'] or 'সক্রিয় নয়'}")

async def claim_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = q.from_user
    ensure_user(u)
    try:
        member = await context.bot.get_chat_member(GROUP_USERNAME, u.id)
        if member.status not in ("member", "administrator", "creator") and not (
            member.status == "restricted" and getattr(member, "is_member", False)
        ):
            await q.message.reply_text("আগে গ্রুপে Join করুন, তারপর Claim চাপুন।")
            return
    except Exception:
        log.exception("Membership check failed")
        await q.message.reply_text("সদস্যপদ যাচাই করা যায়নি। বটকে গ্রুপে Admin করে আবার চেষ্টা করুন।")
        return
    with db() as c:
        if c.execute("SELECT 1 FROM group_claims WHERE user_id=?", (u.id,)).fetchone():
            await q.message.reply_text("আপনি এই Join Reward আগে নিয়েছেন।")
            return
        c.execute("INSERT INTO group_claims(user_id) VALUES(?)", (u.id,))
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (GROUP_JOIN_REWARD, u.id))
    await q.message.reply_text(f"🎉 {GROUP_JOIN_REWARD} {CURRENCY_LABEL} যোগ হয়েছে!")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    if len(context.args) < 3:
        await update.message.reply_text(f"ব্যবহার: /withdraw পরিমাণ বিকাশ/নগদ অ্যাকাউন্ট\nসর্বনিম্ন {MIN_WITHDRAW}")
        return
    try:
        amount = float(context.args[0])
        if amount < MIN_WITHDRAW:
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"সর্বনিম্ন {MIN_WITHDRAW} {CURRENCY_LABEL} লিখুন।")
        return
    method, account = context.args[1], " ".join(context.args[2:])
    uid = update.effective_user.id
    with db() as c:
        row = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row or row["balance"] < amount:
            await update.message.reply_text("পর্যাপ্ত ব্যালেন্স নেই।")
            return
        c.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amount, uid))
        cur = c.execute("INSERT INTO withdrawals(user_id,amount,method,account) VALUES(?,?,?,?)",
                        (uid, amount, method, account))
        wid = cur.lastrowid
    try:
        await context.bot.send_message(ADMIN_ID,
            f"নতুন Withdraw আবেদন #{wid}\nUser: {uid}\nAmount: {amount}\nMethod: {method}\nAccount: {account}")
    except Exception:
        log.exception("Could not notify admin")
    await update.message.reply_text("আবেদন জমা হয়েছে। অ্যাডমিন ম্যানুয়ালি যাচাই ও পেমেন্ট করবেন।")

async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⭐ VIP মেম্বারশিপ\nVIP প্যাকেজ ও মূল্য অ্যাডমিনের কাছ থেকে জেনে নিন: @ItsArman36\n"
        "এই প্রজেক্টে এখনো স্বয়ংক্রিয় বিকাশ/নগদ পেমেন্ট যুক্ত নেই।"
    )

async def addvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("শুধু Admin ব্যবহার করতে পারবেন।")
        return
    raw = " ".join(context.args)
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 4:
        await update.message.reply_text("ফরম্যাট:\n/addvideo Title | Video_URL | Reward | Minimum_Seconds")
        return
    title, url = parts[0], parts[1]
    try:
        reward, seconds = float(parts[2]), int(parts[3])
        if reward <= 0 or seconds < 5 or not url.startswith(("https://", "http://")):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Reward ধনাত্মক এবং সময় কমপক্ষে ৫ সেকেন্ড দিন; URL সঠিক হতে হবে।")
        return
    with db() as c:
        cur = c.execute("INSERT INTO videos(title,url,reward,min_seconds) VALUES(?,?,?,?)",
                        (title, url, reward, seconds))
    await update.message.reply_text(f"ভিডিও #{cur.lastrowid} যোগ হয়েছে।")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("অনুমতি নেই।")
        return
    with db() as c:
        users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        claims = c.execute("SELECT COUNT(*) n FROM video_claims").fetchone()["n"]
        pending = c.execute("SELECT COUNT(*) n FROM withdrawals WHERE status='pending'").fetchone()["n"]
    await update.message.reply_text(f"Users: {users}\nVideo claims: {claims}\nPending withdrawals: {pending}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - শুরু\n/balance - ব্যালেন্স\n/withdraw পরিমাণ বিকাশ/নগদ নম্বর - Withdraw আবেদন\n"
        "/vip - VIP তথ্য\n/addvideo Title | URL | Reward | Seconds - Admin only\n/stats - Admin only"
    )

def run_bot():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN সেট করা নেই। .env ফাইলে নতুন BotFather token দিন।")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("vip", vip))
    app.add_handler(CommandHandler("addvideo", addvideo))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(claim_group, pattern="^claim_group$"))
    log.info("Arman bot polling started")
    app.run_polling()
