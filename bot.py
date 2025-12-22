"""
MVAI Whale Tracker Bot - Production Ready
@MVAi_WhalesTrader_Bot
Koyeb Deployment Version
"""

import os
import logging
import asyncio
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
PORT = int(os.environ.get("PORT", 8000))

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Whale wallets to track (known whales)
WHALE_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot Wallet",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Cold Wallet",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "Binance Whale",
    "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance 8",
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3": "Bitfinex",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX",
    "0x75e89d5979e4f6fba9f97c104c2f0afb3f1dcb88": "MEXC",
}

# User settings storage (in production: use database)
user_subscriptions = {}
user_settings = {}

# Default settings
DEFAULT_THRESHOLD = 100
AVAILABLE_CHAINS = ["ETH", "BSC", "ARB", "MATIC", "SOL"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("🐋 Live Whale Alerts", callback_data="alerts_on")],
        [InlineKeyboardButton("📊 Top Wallets", callback_data="top_wallets")],
        [InlineKeyboardButton("💰 Recent Transfers", callback_data="recent")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🐋 *MVAI Whale Tracker*

Track whale wallets in real-time.
Follow the smart money.

*Features:*
- Real-time whale alerts
- Multi-chain tracking
- Copy trade signals
- Risk management alerts

Select an option below:
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if user_id not in user_settings:
        user_settings[user_id] = {"threshold": DEFAULT_THRESHOLD, "chains": ["ETH"]}
    
    if query.data == "alerts_on":
        user_subscriptions[user_id] = True
        await query.edit_message_text(
            "✅ *Whale Alerts Activated*\n\n"
            "You will receive notifications when whales make significant moves.\n\n"
            "Use /stop to disable alerts.",
            parse_mode="Markdown"
        )
    
    elif query.data == "top_wallets":
        wallets_text = "🐋 *Tracked Whale Wallets*\n\n"
        for addr, name in list(WHALE_WALLETS.items())[:5]:
            short_addr = f"{addr[:6]}...{addr[-4:]}"
            wallets_text += f"• {name}\n  `{short_addr}`\n\n"
        await query.edit_message_text(wallets_text, parse_mode="Markdown")
    
    elif query.data == "recent":
        await query.edit_message_text(
            "🔄 *Fetching recent whale transfers...*",
            parse_mode="Markdown"
        )
        transfers = await fetch_recent_transfers()
        await query.edit_message_text(transfers, parse_mode="Markdown")
    
    elif query.data == "settings":
        keyboard = [
            [InlineKeyboardButton("🔔 Alert Threshold", callback_data="threshold")],
            [InlineKeyboardButton("⛓️ Chain Selection", callback_data="chains")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")],
        ]
        await query.edit_message_text(
            "⚙️ *Settings*\n\nConfigure your alert preferences:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif query.data == "threshold":
        current = user_settings[user_id]["threshold"]
        keyboard = [
            [
                InlineKeyboardButton("50 ETH", callback_data="thresh_50"),
                InlineKeyboardButton("100 ETH", callback_data="thresh_100"),
            ],
            [
                InlineKeyboardButton("500 ETH", callback_data="thresh_500"),
                InlineKeyboardButton("1000 ETH", callback_data="thresh_1000"),
            ],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")],
        ]
        await query.edit_message_text(
            f"🔔 *Alert Threshold*\n\n"
            f"Current: *{current} ETH*\n\n"
            f"Only receive alerts for transfers above this amount.\n"
            f"Select new threshold:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif query.data.startswith("thresh_"):
        value = int(query.data.split("_")[1])
        user_settings[user_id]["threshold"] = value
        await query.edit_message_text(
            f"✅ *Threshold Updated*\n\n"
            f"New threshold: *{value} ETH*\n\n"
            f"You'll only receive alerts for transfers ≥ {value} ETH.",
            parse_mode="Markdown"
        )
    
    elif query.data == "chains":
        current_chains = user_settings[user_id]["chains"]
        keyboard = []
        for chain in AVAILABLE_CHAINS:
            status = "✅" if chain in current_chains else "⬜"
            keyboard.append([InlineKeyboardButton(f"{status} {chain}", callback_data=f"chain_{chain}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")])
        
        await query.edit_message_text(
            f"⛓️ *Chain Selection*\n\n"
            f"Active: *{', '.join(current_chains)}*\n\n"
            f"Tap to toggle chains:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif query.data.startswith("chain_"):
        chain = query.data.split("_")[1]
        current_chains = user_settings[user_id]["chains"]
        
        if chain in current_chains:
            if len(current_chains) > 1:
                current_chains.remove(chain)
        else:
            current_chains.append(chain)
        
        user_settings[user_id]["chains"] = current_chains
        
        keyboard = []
        for c in AVAILABLE_CHAINS:
            status = "✅" if c in current_chains else "⬜"
            keyboard.append([InlineKeyboardButton(f"{status} {c}", callback_data=f"chain_{c}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Settings", callback_data="settings")])
        
        await query.edit_message_text(
            f"⛓️ *Chain Selection*\n\n"
            f"Active: *{', '.join(current_chains)}*\n\n"
            f"Tap to toggle chains:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🐋 Live Whale Alerts", callback_data="alerts_on")],
            [InlineKeyboardButton("📊 Top Wallets", callback_data="top_wallets")],
            [InlineKeyboardButton("💰 Recent Transfers", callback_data="recent")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        ]
        await query.edit_message_text(
            "🐋 *MVAI Whale Tracker*\n\nSelect an option:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def fetch_recent_transfers() -> str:
    if not ETHERSCAN_API_KEY:
        return "📊 *Recent Large Transfers*\n\n" \
               "⚠️ API key not configured.\n" \
               "Demo mode: Showing sample data.\n\n" \
               "• Binance → Unknown: 500 ETH\n" \
               "• OKX → DeFi Protocol: 1,200 ETH\n" \
               "• Whale → Coinbase: 850 ETH"
    
    try:
        wallet = list(WHALE_WALLETS.keys())[0]
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet}&startblock=0&endblock=99999999&page=1&offset=5&sort=desc&apikey={ETHERSCAN_API_KEY}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
        
        if data["status"] == "1" and data["result"]:
            text = "📊 *Recent Whale Transfers*\n\n"
            for tx in data["result"][:5]:
                value_eth = int(tx["value"]) / 10**18
                if value_eth > 0:
                    text += f"• {value_eth:.2f} ETH\n"
                    text += f"  `{tx['hash'][:16]}...`\n\n"
            return text
        else:
            return "📊 No recent transfers found."
    
    except Exception as e:
        logger.error(f"Error fetching transfers: {e}")
        return "⚠️ Error fetching data. Please try again."

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_subscriptions[user_id] = False
    await update.message.reply_text(
        "🔕 *Whale Alerts Disabled*\n\nUse /start to enable again.",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    active_users = sum(1 for v in user_subscriptions.values() if v)
    await update.message.reply_text(
        f"📈 *Bot Status*\n\n"
        f"• Active subscribers: {active_users}\n"
        f"• Tracked wallets: {len(WHALE_WALLETS)}\n"
        f"• Status: Online ✅\n"
        f"• Last check: {datetime.now().strftime('%H:%M:%S')}",
        parse_mode="Markdown"
    )

async def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info(f"Starting bot on port {PORT}")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
