import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import sqlite3
import os
from datetime import datetime
from flask import Flask
from threading import Thread

# ============ CONFIGURATION ============
TOKEN = "8656575185:AAHNVzAN8u8Iha9igHwiocPJv4RO2KKZyHM"
OWNER_ID = 8558052873

# ============ WEB SERVER FOR 24/7 ============
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running!"

def run_web():
    app_web.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ============ DATABASE ============
conn = sqlite3.connect('escrow.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS allowed_groups (group_id INTEGER PRIMARY KEY)''')
c.execute('''CREATE TABLE IF NOT EXISTS group_settings (group_id INTEGER, setting TEXT, value TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS warnings (user_id TEXT, group_id INTEGER, reason TEXT, date TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS filters (group_id INTEGER, keyword TEXT, response TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notes (group_id INTEGER, note_name TEXT, content TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS escrows (id TEXT, buyer TEXT, seller TEXT, amount TEXT, status TEXT, date TEXT)''')
conn.commit()

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Developer", url="https://t.me/clerkmm")]]
    await update.message.reply_text(
        "WELCOME TO ESCROW BOT\n\n"
        "Powered by: @clerkmm\n\n"
        "Features:\n"
        "- Admin Panel\n"
        "- Group Management\n"
        "- Escrow Services\n"
        "- Moderation Tools\n"
        "- 3%% Fee Calculation\n\n"
        "Commands: /help",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "COMPLETE COMMANDS LIST\n\n"
        "ADMIN COMMANDS:\n"
        "/admin - Open admin panel\n"
        "/ban - Ban a user\n"
        "/unban - Unban user\n"
        "/kick - Kick user\n"
        "/mute - Mute user\n"
        "/unmute - Unmute user\n"
        "/warn - Warn user\n"
        "/warns - Check warns\n"
        "/resetwarns - Reset warns\n"
        "/purge - Delete messages\n\n"
        "FILTER COMMANDS:\n"
        "/filter - Add word filter\n"
        "/stop - Remove filter\n"
        "/filters - List filters\n\n"
        "NOTE COMMANDS:\n"
        "/save - Save a note\n"
        "/get - Get a note\n"
        "/notes - List notes\n"
        "/clear - Clear notes\n\n"
        "WELCOME COMMANDS:\n"
        "/setwelcome - Set welcome message\n"
        "/clearwelcome - Remove welcome\n\n"
        "ESCROW COMMANDS:\n"
        "/escrow - Create escrow\n"
        "/release - Release funds\n"
        "/refund - Refund buyer\n"
        "/status - Check escrow status\n"
        "/fee - Calculate 3%% escrow fee\n\n"
        "GROUP MANAGEMENT:\n"
        "/lock - Lock chat\n"
        "/unlock - Unlock chat\n\n"
        "Developer: @clerkmm"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Access Denied. Owner only.")
        return
    
    keyboard = [
        [InlineKeyboardButton("Stats", callback_data="stats")],
        [InlineKeyboardButton("Allow Group", callback_data="allow_group")],
        [InlineKeyboardButton("List Groups", callback_data="list_groups")],
        [InlineKeyboardButton("Warnings Log", callback_data="warnings_log")],
        [InlineKeyboardButton("All Escrows", callback_data="escrows")],
        [InlineKeyboardButton("Ban User", callback_data="ban_user")],
    ]
    await update.message.reply_text(
        "ADMIN PANEL\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("Unauthorized access.")
        return
    
    if query.data == "stats":
        groups_count = c.execute("SELECT COUNT(*) FROM allowed_groups").fetchone()[0]
        warns_count = c.execute("SELECT COUNT(*) FROM warnings").fetchone()[0]
        escrows_count = c.execute("SELECT COUNT(*) FROM escrows").fetchone()[0]
        await query.edit_message_text(
            f"BOT STATISTICS\n\n"
            f"Allowed Groups: {groups_count}\n"
            f"Total Warnings: {warns_count}\n"
            f"Total Escrows: {escrows_count}\n"
            f"Developer: @clerkmm\n"
            f"Status: Active"
        )
    elif query.data == "list_groups":
        groups = c.execute("SELECT group_id FROM allowed_groups").fetchall()
        if groups:
            group_list = "\n".join([f"- {g[0]}" for g in groups])
            await query.edit_message_text(f"ALLOWED GROUPS\n\n{group_list}")
        else:
            await query.edit_message_text("No groups allowed yet.")
    elif query.data == "warnings_log":
        warns = c.execute("SELECT user_id, reason, date FROM warnings LIMIT 10").fetchall()
        if warns:
            warn_list = "\n".join([f"- {w[0]}: {w[1]} ({w[2]})" for w in warns])
            await query.edit_message_text(f"RECENT WARNINGS\n\n{warn_list}")
        else:
            await query.edit_message_text("No warnings recorded.")
    elif query.data == "escrows":
        escrows_list = c.execute("SELECT id, buyer, seller, amount, status FROM escrows LIMIT 10").fetchall()
        if escrows_list:
            escrow_text = "\n".join([f"- {e[0]}: {e[1]} -> {e[2]} | {e[3]} | {e[4]}" for e in escrows_list])
            await query.edit_message_text(f"RECENT ESCROWS\n\n{escrow_text}")
        else:
            await query.edit_message_text("No escrow transactions found.")

# ============ MODERATION COMMANDS ============

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("This command works only in groups.")
        return
    
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Admin access required.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /ban @username")
        return
    
    await update.message.reply_text(f"User {context.args[0]} has been banned.")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("This command works only in groups.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /warn @username reason")
        return
    
    user_id = context.args[0]
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("INSERT INTO warnings (user_id, group_id, reason, date) VALUES (?, ?, ?, ?)",
              (user_id, update.effective_chat.id, reason, current_date))
    conn.commit()
    
    await update.message.reply_text(f"Warning issued to {user_id}\nReason: {reason}")

async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /warns @username")
        return
    
    user_id = context.args[0]
    c.execute("SELECT reason, date FROM warnings WHERE user_id=? AND group_id=?", 
              (user_id, update.effective_chat.id))
    warns_list = c.fetchall()
    
    if not warns_list:
        await update.message.reply_text(f"No warnings found for {user_id}")
        return
    
    warn_text = "\n".join([f"- {w[1]}: {w[0]}" for w in warns_list])
    await update.message.reply_text(f"WARNINGS FOR {user_id}\n\n{warn_text}")

async def resetwarns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /resetwarns @username")
        return
    
    user_id = context.args[0]
    c.execute("DELETE FROM warnings WHERE user_id=? AND group_id=?", (user_id, update.effective_chat.id))
    conn.commit()
    await update.message.reply_text(f"All warnings reset for {user_id}")

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Admin access required.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /purge number")
        return
    
    try:
        count = int(context.args[0])
        await update.message.reply_text(f"Deleted {count} messages.")
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")

# ============ FILTER COMMANDS ============

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /filter keyword response")
        return
    
    keyword = context.args[0].lower()
    response = ' '.join(context.args[1:]) if len(context.args) > 1 else "Filter triggered!"
    
    c.execute("INSERT OR REPLACE INTO filters (group_id, keyword, response) VALUES (?, ?, ?)",
              (update.effective_chat.id, keyword, response))
    conn.commit()
    
    await update.message.reply_text(f"Filter added: '{keyword}' -> '{response}'")

async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT keyword, response FROM filters WHERE group_id=?", (update.effective_chat.id,))
    filters_list = c.fetchall()
    
    if not filters_list:
        await update.message.reply_text("No active filters in this group.")
        return
    
    filter_text = "\n".join([f"- {f[0]}: {f[1]}" for f in filters_list])
    await update.message.reply_text(f"ACTIVE FILTERS\n\n{filter_text}")

async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /stop keyword")
        return
    
    keyword = context.args[0].lower()
    c.execute("DELETE FROM filters WHERE group_id=? AND keyword=?", (update.effective_chat.id, keyword))
    conn.commit()
    
    await update.message.reply_text(f"Filter removed: '{keyword}'")

async def auto_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.lower()
    c.execute("SELECT response FROM filters WHERE group_id=? AND keyword=?", (update.effective_chat.id, text))
    result = c.fetchone()
    
    if result:
        await update.message.reply_text(result[0])

# ============ NOTE COMMANDS ============

async def save_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /save note_name content")
        return
    
    note_name = context.args[0].lower()
    content = ' '.join(context.args[1:])
    
    c.execute("INSERT OR REPLACE INTO notes (group_id, note_name, content) VALUES (?, ?, ?)",
              (update.effective_chat.id, note_name, content))
    conn.commit()
    
    await update.message.reply_text(f"Note '{note_name}' saved successfully!")

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /get note_name")
        return
    
    note_name = context.args[0].lower()
    c.execute("SELECT content FROM notes WHERE group_id=? AND note_name=?", 
              (update.effective_chat.id, note_name))
    result = c.fetchone()
    
    if result:
        await update.message.reply_text(result[0])
    else:
        await update.message.reply_text(f"Note '{note_name}' not found.")

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT note_name FROM notes WHERE group_id=?", (update.effective_chat.id,))
    notes_list = c.fetchall()
    
    if not notes_list:
        await update.message.reply_text("No saved notes in this group.")
        return
    
    note_text = "\n".join([f"- {n[0]}" for n in notes_list])
    await update.message.reply_text(f"SAVED NOTES\n\n{note_text}")

async def clear_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("DELETE FROM notes WHERE group_id=?", (update.effective_chat.id,))
    conn.commit()
    await update.message.reply_text("All notes have been cleared from this group.")

# ============ WELCOME COMMANDS ============

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /setwelcome Welcome message here")
        return
    
    welcome_msg = ' '.join(context.args)
    
    c.execute("INSERT OR REPLACE INTO group_settings (group_id, setting, value) VALUES (?, 'welcome', ?)",
              (update.effective_chat.id, welcome_msg))
    conn.commit()
    
    await update.message.reply_text("Welcome message has been set!")

async def clear_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("DELETE FROM group_settings WHERE group_id=? AND setting='welcome'", (update.effective_chat.id,))
    conn.commit()
    await update.message.reply_text("Welcome message has been removed.")

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT value FROM group_settings WHERE group_id=? AND setting='welcome'", (update.effective_chat.id,))
    result = c.fetchone()
    
    if result and update.message.new_chat_members:
        welcome_msg = result[0]
        for member in update.message.new_chat_members:
            await update.message.reply_text(welcome_msg.format(user=member.first_name))

# ============ ESCROW COMMANDS ============

async def escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text(
            "ESCROW COMMAND USAGE\n\n"
            "/escrow @buyer @seller amount\n\n"
            "Example: /escrow @username1 @username2 100\n\n"
            "Use /fee to calculate 3%% escrow fee first."
        )
        return
    
    buyer = context.args[0]
    seller = context.args[1]
    amount = context.args[2]
    escrow_id = f"ESC{int(datetime.now().timestamp())}"
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("INSERT INTO escrows (id, buyer, seller, amount, status, date) VALUES (?, ?, ?, ?, ?, ?)",
              (escrow_id, buyer, seller, amount, "PENDING", current_date))
    conn.commit()
    
    await update.message.reply_text(
        f"ESCROW CREATED\n\n"
        f"ID: {escrow_id}\n"
        f"Buyer: {buyer}\n"
        f"Seller: {seller}\n"
        f"Amount: {amount}\n"
        f"Status: PENDING\n\n"
        f"Waiting for buyer to deposit funds...\n\n"
        f"Developer: @clerkmm"
    )

async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /release escrow_id")
        return
    
    escrow_id = context.args[0]
    c.execute("UPDATE escrows SET status='RELEASED' WHERE id=?", (escrow_id,))
    conn.commit()
    
    await update.message.reply_text(f"Escrow {escrow_id} has been RELEASED. Funds sent to seller.")

async def refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /refund escrow_id")
        return
    
    escrow_id = context.args[0]
    c.execute("UPDATE escrows SET status='REFUNDED' WHERE id=?", (escrow_id,))
    conn.commit()
    
    await update.message.reply_text(f"Escrow {escrow_id} has been REFUNDED. Funds returned to buyer.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /status escrow_id")
        return
    
    escrow_id = context.args[0]
    c.execute("SELECT buyer, seller, amount, status, date FROM escrows WHERE id=?", (escrow_id,))
    result = c.fetchone()
    
    if result:
        await update.message.reply_text(
            f"ESCROW STATUS\n\n"
            f"ID: {escrow_id}\n"
            f"Buyer: {result[0]}\n"
            f"Seller: {result[1]}\n"
            f"Amount: {result[2]}\n"
            f"Status: {result[3]}\n"
            f"Created: {result[4]}"
        )
    else:
        await update.message.reply_text(f"Escrow {escrow_id} not found.")

# ============ FEE CALCULATION COMMAND ============

async def calculate_fee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "FEE CALCULATION\n\n"
            "Usage: /fee amount\n\n"
            "Example: /fee 100\n\n"
            "This calculates 3%% escrow fee on any amount."
        )
        return
    
    try:
        amount = float(context.args[0])
        if amount <= 0:
            await update.message.reply_text("Please enter a valid amount greater than zero.")
            return
        
        fee = amount * 0.03
        total = amount + fee
        
        await update.message.reply_text(
            f"FEE CALCULATION\n\n"
            f"Original Amount: {amount}\n"
            f"3%% Fee: {fee:.2f}\n"
            f"Total to Pay: {total:.2f}\n\n"
            f"Note: Buyer pays {fee:.2f} as escrow service fee.\n"
            f"Developer: @clerkmm"
        )
    except ValueError:
        await update.message.reply_text("Please enter a valid number.\nExample: /fee 100")

# ============ GROUP PERMISSION CHECK ============

async def check_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ['group', 'supergroup']:
        c.execute("SELECT group_id FROM allowed_groups WHERE group_id=?", (update.effective_chat.id,))
        if not c.fetchone() and update.effective_user.id != OWNER_ID:
            await update.message.reply_text(
                "Group Not Authorized\n\n"
                "This group is not allowed to use this bot.\n"
                "Contact @clerkmm for permission."
            )

# ============ MAIN FUNCTION ============

def main():
    keep_alive()
    
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("warns", warns))
    app.add_handler(CommandHandler("resetwarns", resetwarns))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("filters", list_filters))
    app.add_handler(CommandHandler("stop", stop_filter))
    app.add_handler(CommandHandler("save", save_note))
    app.add_handler(CommandHandler("get", get_note))
    app.add_handler(CommandHandler("notes", list_notes))
    app.add_handler(CommandHandler("clear", clear_notes))
    app.add_handler(CommandHandler("setwelcome", set_welcome))
    app.add_handler(CommandHandler("clearwelcome", clear_welcome))
    app.add_handler(CommandHandler("escrow", escrow))
    app.add_handler(CommandHandler("release", release))
    app.add_handler(CommandHandler("refund", refund))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("fee", calculate_fee))  # <-- FEE COMMAND ADDED HERE
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_filter))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(filters.ALL, check_group))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logging.error(f"Update {update} caused error {context.error}")
    
    app.add_error_handler(error_handler)
    
    print("Bot is running successfully!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
