#!/usr/bin/env python3
"""
Telegram AI Bot with Admin System, Safety Filter, and OpenCode Integration
"""

import os
import json
import logging
from datetime import datetime
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8640273285:AAGWMAtnlEsgFhKwSbJYwB452vXs3vV5y1k"
ADMIN_IDS = [7731990023]  # Add your admin Telegram ID here
# Using Groq - free AI API
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")  # Free tier
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set")

# File to store user data
DATA_FILE = "bot_data.json"

# ==================== SAFETY FILTER ====================
class SafetyFilter:
    """Classify messages as safe, unsafe, or unknown"""
    
    UNSAFE_KEYWORDS = [
        "hack", "steal", "bypass", "crack", "malware", "virus",
        "phishing", "ddos", "exploit", "vulnerability", "attack",
        "illegal", "fraud", "scam", "spam", "botnet"
    ]
    
    SAFE_KEYWORDS = [
        "code", "python", "programming", "function", "class",
        "api", "how to", "tutorial", "learn", "example",
        "debug", "error", "help", "question"
    ]
    
    @classmethod
    def classify(cls, text: str) -> str:
        text_lower = text.lower()
        for keyword in cls.UNSAFE_KEYWORDS:
            if keyword in text_lower:
                return "unsafe"
        for keyword in cls.SAFE_KEYWORDS:
            if keyword in text_lower:
                return "safe"
        return "unknown"
    
    @classmethod
    def is_unsafe_request(cls, text: str) -> bool:
        return cls.classify(text) == "unsafe"


# ==================== USER PROFILE SYSTEM ====================
class UserProfile:
    def __init__(self):
        self.data = self.load_data()
    
    def load_data(self) -> dict:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        return {"users": {}, "pending": [], "blocked": []}
    
    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def add_user(self, user_id: int, username: str, first_name: str):
        if str(user_id) not in self.data["users"]:
            self.data["users"][str(user_id)] = {
                "id": user_id,
                "username": username,
                "first_name": first_name,
                "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "messages": 0,
                "approved": True
            }
            self.save_data()
    
    def increment_messages(self, user_id: int):
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["messages"] += 1
            self.save_data()
    
    def get_user(self, user_id: int) -> dict:
        return self.data["users"].get(str(user_id))
    
    def approve_user(self, user_id: int):
        if user_id in self.data["pending"]:
            self.data["pending"].remove(user_id)
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["approved"] = True
            self.save_data()
    
    def block_user(self, user_id: int):
        if user_id not in self.data["blocked"]:
            self.data["blocked"].append(user_id)
            self.save_data()
    
    def unblock_user(self, user_id: int):
        if user_id in self.data["blocked"]:
            self.data["blocked"].remove(user_id)
            self.save_data()
    
    def is_blocked(self, user_id: int) -> bool:
        return user_id in self.data["blocked"]


user_profile = UserProfile()


# ==================== OPENCODE AI INTEGRATION ====================
async def ask_opencode(question: str) -> str:
    try:
        import aiohttp
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": question}],
            "temperature": 0.7
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_API_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    data = await response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        return data["choices"][0]["message"]["content"]
                    return str(data)
                return f"API Error: {response.status} - {await response.text()}"
    except ImportError:
        return "Need aiohttp: pip install aiohttp"
    except Exception as e:
        logger.error(f"AI error: {e}")
        return f"Error: {str(e)}"


# ==================== DECORATORS ====================
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Admin only.")
            return
        return await func(update, context)
    return wrapper


def blocked_handler(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if user_profile.is_blocked(update.effective_user.id):
            await update.message.reply_text("⛔ You are blocked.")
            return
        return await func(update, context)
    return wrapper


# ==================== COMMAND HANDLERS ====================
@blocked_handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_profile.add_user(user.id, user.username or "N/A", user.first_name)
    await update.message.reply_text(
        f"👋 Welcome {user.first_name}!\n\n"
        "I'm an AI bot.\n\n"
        "Commands:\n"
        "/profile - Your profile\n"
        "/code <question> - Ask coding questions\n"
        "/help - Help"
    )


@blocked_handler
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = user_profile.get_user(update.effective_user.id)
    if profile:
        await update.message.reply_text(
            f"👤 Profile\n\n"
            f"ID: {profile['id']}\n"
            f"Name: {profile['first_name']}\n"
            f"Username: @{profile['username']}\n"
            f"Joined: {profile['joined']}\n"
            f"Messages: {profile['messages']}"
        )
    else:
        await update.message.reply_text("❌ No profile found.")


@blocked_handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Commands:\n\n"
        "/start - Start bot\n"
        "/profile - View profile\n"
        "/code <question> - Ask coding question\n"
        "/help - This help\n\n"
        "Admin: /admin, /approve, /block, /unblock"
    )


@blocked_handler
async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❓ Ask a question: /code how do I...")
        return
    
    question = " ".join(context.args)
    await update.message.reply_text("🤔 Thinking...")
    
    if SafetyFilter.is_unsafe_request(question):
        await update.message.reply_text("⚠️ I can't help with that.")
        return
    
    response = await ask_opencode(question)
    await update.message.reply_text(f"🤖 {response}")


# ==================== ADMIN COMMANDS ====================
@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Stats", callback_data="admin_stats")]
    ]
    await update.message.reply_text("🔧 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))


@admin_only
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /approve <user_id>")
        return
    try:
        user_id = int(context.args[0])
        user_profile.approve_user(user_id)
        await update.message.reply_text(f"✅ User {user_id} approved!")
    except:
        await update.message.reply_text("❌ Invalid ID.")


@admin_only
async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /block <user_id>")
        return
    try:
        user_id = int(context.args[0])
        user_profile.block_user(user_id)
        await update.message.reply_text(f"⛔ User {user_id} blocked!")
    except:
        await update.message.reply_text("❌ Invalid ID.")


@admin_only
async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /unblock <user_id>")
        return
    try:
        user_id = int(context.args[0])
        user_profile.unblock_user(user_id)
        await update.message.reply_text(f"✅ User {user_id} unblocked!")
    except:
        await update.message.reply_text("❌ Invalid ID.")


# ==================== CALLBACK HANDLER ====================
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_stats":
        users = user_profile.data.get("users", {})
        await query.edit_message_text(
            f"📊 Stats\n\n"
            f"Users: {len(users)}\n"
            f"Blocked: {len(user_profile.data.get('blocked', []))}"
        )


# ==================== MESSAGE HANDLER ====================
@blocked_handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_profile.add_user(user.id, user.username or "N/A", user.first_name)
    user_profile.increment_messages(user.id)
    
    text = update.message.text
    
    # Send ALL messages to OpenCode AI
    await update.message.reply_text("🤔 Thinking...")
    response = await ask_opencode(text)
    
    # Send response (split if too long)
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            await update.message.reply_text(response[i:i+4000])
    else:
        await update.message.reply_text(response)


# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
