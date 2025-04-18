from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from tinydb import TinyDB, Query
from datetime import datetime, timedelta
from flask import Flask
import threading

# Telegram Token and Admin ID
BOT_TOKEN = "7933179905:AAG0fFJcGHinuAJeFeGkDT2SNwbXl5eKjq4"
ADMIN_ID = 7993514257

# Database
db = TinyDB('database.json')
users_table = db.table('users')
ref_table = db.table('referrals')
withdraw_table = db.table('withdraws')
bonus_table = db.table('bonus')

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if args:
        referrer_id = args[0]
        if user_id != int(referrer_id):
            if not ref_table.contains(Query().user_id == user_id):
                ref_table.insert({'user_id': user_id, 'referrer': int(referrer_id)})
                ref_user = users_table.get(Query().user_id == int(referrer_id))
                if ref_user:
                    users_table.update({'points': ref_user['points'] + 5}, Query().user_id == int(referrer_id))
                else:
                    users_table.insert({'user_id': int(referrer_id), 'points': 5})

                await context.bot.send_message(chat_id=int(referrer_id), text="🎉 Ek naya referral mila! +5 points")

    if not users_table.contains(Query().user_id == user_id):
        users_table.insert({'user_id': user_id, 'points': 0})

    await update.message.reply_text(
        "👋 Swagat hai!\nCommands:\n"
        "/refer - Apna referral link lo\n"
        "/points - Points dekho\n"
        "/top - Top referrers\n"
        "/withdraw - Points redeem karo\n"
        "/dailybonus - Roz ka bonus lo"
    )

# /refer
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    refer_link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(f"🔗 Referral link:\n{refer_link}")

# /points
async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users_table.get(Query().user_id == user_id)
    pts = user['points'] if user else 0
    await update.message.reply_text(f"💰 Aapke paas {pts} points hain.")

# /top
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_users = users_table.all()
    top_users = sorted(all_users, key=lambda x: x['points'], reverse=True)[:5]
    msg = "🏆 Top Referrers:\n"
    for i, user in enumerate(top_users):
        msg += f"{i+1}. User ID: {user['user_id']} - {user['points']} pts\n"
    await update.message.reply_text(msg)

# /dailybonus
async def dailybonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.now().date()
    bonus_record = bonus_table.get(Query().user_id == user_id)

    if bonus_record and bonus_record['date'] == str(today):
        await update.message.reply_text("⛔ Aaj ka bonus le chuke ho!")
        return

    user = users_table.get(Query().user_id == user_id)
    if user:
        users_table.update({'points': user['points'] + 2}, Query().user_id == user_id)
    else:
        users_table.insert({'user_id': user_id, 'points': 2})

    bonus_table.upsert({'user_id': user_id, 'date': str(today)}, Query().user_id == user_id)
    await update.message.reply_text("🎁 Aapko 2 bonus points mile!")

# /withdraw
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = users_table.get(Query().user_id == user_id)
    if user and user['points'] >= 20:
        users_table.update({'points': user['points'] - 20}, Query().user_id == user_id)
        withdraw_table.insert({'user_id': user_id, 'status': 'Pending'})
        await update.message.reply_text("✅ Withdraw request bhej diya gaya hai.")
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"Withdraw request from {user_id}")
    else:
        await update.message.reply_text("❌ Withdraw ke liye kam se kam 20 points chahiye.")

# /broadcast (admin only)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Sirf admin ke liye!")
        return

    msg = " ".join(context.args)
    all_users = users_table.all()
    for u in all_users:
        try:
            await context.bot.send_message(chat_id=u['user_id'], text=f"📢 Broadcast:\n{msg}")
        except:
            pass
    await update.message.reply_text("✅ Broadcast bhej diya gaya.")

# /admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text("👑 Welcome Admin!\nUse /broadcast <msg>")
    else:
        await update.message.reply_text("⛔ Admin panel sirf malik ke liye hai!")

# Flask server for Uptime
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# Main function
def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("refer", refer))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("dailybonus", dailybonus))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("admin", admin))

    print("BOT IS RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
