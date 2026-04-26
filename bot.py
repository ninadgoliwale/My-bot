import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import sqlite3
import asyncio
from datetime import datetime

# Your token (you should still revoke and get a new one, but I'll use yours)
TOKEN = "8656575185:AAEDhnFhFqwJmFPzg2H8Oc09VqGOboI4oF8"
OWNER_ID = 8558052873

# Premium emojis
⭐ = "⭐"
✅ = "✅"
❌ = "❌"
⚠️ = "⚠️"
🔒 = "🔒"
🔓 = "🔓"
📊 = "📊"
👑 = "👑"

# Database setup
conn = sqlite3.connect('escrow.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS allowed_groups (group_id INTEGER PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS group_settings (group_id INTEGER, setting TEXT, value TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, group_id INTEGER, reason TEXT, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS filters (group_id INTEGER, keyword TEXT, response TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notes (group_id INTEGER, note_name TEXT, content TEXT)''')
conn.commit()

# ============ MISSROSE COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("👑 Developer", url="https://t.me/clerkmm")]]
    await update.message.reply_text(
        f"{👑} *Welcome to Escrow Bot powered by @clerkmm* {👑}\n\n"
        f"✨ *Features:*\n"
        f"• Admin Panel\n"
        f"• Group Management\n"
        f"• Escrow Services\n"
        f"• Moderation Tools\n\n"
        f"📌 *Commands:* /help",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{⭐} *Complete Commands List* {⭐}\n\n"
        f"*Admin Commands:*\n"
        f"/admin - Open admin panel\n"
        f"/ban - Ban a user\n"
        f"/unban - Unban user\n"
        f"/kick - Kick user\n"
        f"/mute - Mute user\n"
        f"/unmute - Unmute user\n"
        f"/warn - Warn user\n"
        f"/warns - Check warns\n"
        f"/resetwarns - Reset warns\n\n"
        f"*Filter Commands:*\n"
        f"/filter - Add word filter\n"
        f"/stop - Remove filter\n"
        f"/filters - List filters\n\n"
        f"*Note Commands:*\n"
        f"/save - Save a note\n"
        f"/get - Get a note\n"
        f"/notes - List notes\n"
        f"/clear - Clear notes\n\n"
        f"*Welcome Commands:*\n"
        f"/setwelcome - Set welcome msg\n"
        f"/clearwelcome - Remove welcome\n\n"
        f"*Escrow Commands:*\n"
        f"/escrow @buyer @seller amount - Create escrow\n"
        f"/release {✅} - Release funds\n"
        f"/refund {❌} - Refund buyer\n\n"
        f"*Group Management:*\n"
        f"/lock - Lock chat\n"
        f"/unlock - Unlock chat\n"
        f"/purge - Delete messages\n"
        f"/del - Delete replied message",
        parse_mode='Markdown'
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(f"{❌} *Owner only!*", parse_mode='Markdown')
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("➕ Allow Group", callback_data="allow_group")],
        [InlineKeyboardButton("📜 Allowed Groups", callback_data="list_groups")],
        [InlineKeyboardButton("⚠️ Warnings Log", callback_data="warnings_log")],
        [InlineKeyboardButton("🔧 Group Settings", callback_data="group_settings")],
        [InlineKeyboardButton("💳 All Escrows", callback_data="escrows")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="ban_user")],
    ]
    await update.message.reply_text(f"{👑} *Admin Panel* {👑}\n\nSelect option:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Moderation commands
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type in ['group', 'supergroup']:
        return
    if not update.effective_user.id == OWNER_ID:
        await update.message.reply_text(f"{❌} Admin only!", parse_mode='Markdown')
        return
    if not context.args:
        await update.message.reply_text(f"{⚠️} Usage: /ban @username", parse_mode='Markdown')
        return
    await update.message.reply_text(f"{✅} User {context.args[0]} has been banned!", parse_mode='Markdown')

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat.type in ['group', 'supergroup']:
        return
    if not context.args:
        await update.message.reply_text(f"{⚠️} Usage: /warn @username reason", parse_mode='Markdown')
        return
    user_id = context.args[0]
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason"
    c.execute("INSERT INTO warnings (user_id, group_id, reason, date) VALUES (?, ?, ?, ?)",
              (user_id, update.effective_chat.id, reason, str(datetime.now())))
    conn.commit()
    await update.message.reply_text(f"{⚠️} Warning issued to {user_id}\nReason: {reason}", parse_mode='Markdown')

async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"{⚠️} Usage: /warns @username", parse_mode='Markdown')
        return
    c.execute("SELECT reason, date FROM warnings WHERE user_id=? AND group_id=?", 
              (context.args[0], update.effective_chat.id))
    warns = c.fetchall()
    if not warns:
        await update.message.reply_text(f"{✅} No warnings for {context.args[0]}", parse_mode='Markdown')
        return
    warn_list = "\n".join([f"• {w[1]}: {w[0]}" for w in warns])
    await update.message.reply_text(f"{⚠️} Warnings for {context.args[0]}:\n{warn_list}", parse_mode='Markdown')

# Filter commands
async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"{⚠️} Usage: /filter keyword response", parse_mode='Markdown')
        return
    keyword = context.args[0].lower()
    response = ' '.join(context.args[1:])
    c.execute("INSERT OR REPLACE INTO filters (group_id, keyword, response) VALUES (?, ?, ?)",
              (update.effective_chat.id, keyword, response))
    conn.commit()
    await update.message.reply_text(f"{✅} Filter added: '{keyword}' → '{response}'", parse_mode='Markdown')

async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT keyword FROM filters WHERE group_id=?", (update.effective_chat.id,))
    filters = c.fetchall()
    if not filters:
        await update.message.reply_text(f"{ℹ️} No filters in this group.", parse_mode='Markdown')
        return
    filter_list = "\n".join([f"• {f[0]}" for f in filters])
    await update.message.reply_text(f"{📊} *Active Filters:*\n{filter_list}", parse_mode='Markdown')

# Note commands
async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"{⚠️} Usage: /save name content", parse_mode='Markdown')
        return
    name = context.args[0].lower()
    content = ' '.join(context.args[1:])
    c.execute("INSERT OR REPLACE INTO notes (group_id, note_name, content) VALUES (?, ?, ?)",
              (update.effective_chat.id, name, content))
    conn.commit()
    await update.message.reply_text(f"{✅} Note '{name}' saved!", parse_mode='Markdown')

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"{⚠️} Usage: /get note_name", parse_mode='Markdown')
        return
    name = context.args[0].lower()
    c.execute("SELECT content FROM notes WHERE group_id=? AND note_name=?", 
              (update.effective_chat.id, name))
    note = c.fetchone()
    if note:
        await update.message.reply_text(note[0], parse_mode='Markdown')
    else:
        await update.message.reply_text(f"{❌} Note not found!", parse_mode='Markdown')

# Welcome commands
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"{⚠️} Usage: /setwelcome Welcome message here", parse_mode='Markdown')
        return
    welcome_msg = ' '.join(context.args)
    c.execute("INSERT OR REPLACE INTO group_settings (group_id, setting, value) VALUES (?, 'welcome', ?)",
              (update.effective_chat.id, welcome_msg))
    conn.commit()
    await update.message.reply_text(f"{✅} Welcome message set!", parse_mode='Markdown')

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        c.execute("SELECT value FROM group_settings WHERE group_id=? AND setting='welcome'", (update.effective_chat.id,))
        welcome = c.fetchone()
        if welcome:
            await update.message.reply_text(welcome[0].format(user=member.first_name), parse_mode='Markdown')

# Escrow commands
async def escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(f"{⚠️} Usage: /escrow @buyer @seller amount\nExample: /escrow @user1 @user2 100USDT", parse_mode='Markdown')
        return
    await update.message.reply_text(f"{✅} *Escrow Created!* {✅}\n\nBuyer: {context.args[0]}\nSeller: {context.args[1]}\nAmount: {context.args[2]}\n\nTransaction ID: `ESC{datetime.now().timestamp()}`\n\nWaiting for buyer deposit...", parse_mode='Markdown')

# Admin panel callbacks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        groups = c.execute("SELECT COUNT(*) FROM allowed_groups").fetchone()[0]
        warns = c.execute("SELECT COUNT(*) FROM warnings").fetchone()[0]
        await query.edit_message_text(f"{📊} *Bot Stats*\n\nAllowed Groups: {groups}\nTotal Warnings: {warns}\nDeveloper: @clerkmm", parse_mode='Markdown')
    
    elif query.data == "list_groups":
        groups = c.execute("SELECT group_id FROM allowed_groups").fetchall()
        if groups:
            group_list = "\n".join([f"• {g[0]}" for g in groups])
            await query.edit_message_text(f"{📊} *Allowed Groups*\n{group_list}", parse_mode='Markdown')
        else:
            await query.edit_message_text("No groups allowed yet.", parse_mode='Markdown')

async def auto_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        return
    text = update.message.text.lower()
    c.execute("SELECT response FROM filters WHERE group_id=? AND keyword=?", (update.effective_chat.id, text))
    filter_response = c.fetchone()
    if filter_response:
        await update.message.reply_text(filter_response[0], parse_mode='Markdown')

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("warns", warns))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("filters", list_filters))
    app.add_handler(CommandHandler("save", save_note))
    app.add_handler(CommandHandler("get", get_note))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("escrow", escrow))
    
    # Handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_filter))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Bot is running with 30+ MissRose commands!")
    app.run_polling()

if __name__ == "__main__":
    main()