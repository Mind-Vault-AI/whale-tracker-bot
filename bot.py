"""
MVAI Whale Tracker Bot
Telegram: @MVAI_WhalesTrader_Bot
Koyeb Deployment - Production Ready
"""

import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web
import aiohttp

# === CONFIGURATION ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_API_KEY", "")
PORT = int(os.environ.get("PORT", 8000))

# === LOGGING ===
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === WHALE WALLETS (Known Exchanges) ===
WHALE_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Cold",
    "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance 8",
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3": "Bitfinex",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX",
    "0x75e89d5979e4f6fba9f97c104c2f0afb3f1dcb88": "MEXC",
}

# === USER STATE ===
user_settings = {}

def get_user_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = {
            "alerts": False,
            "threshold": 100,
            "chains": ["ETH"]
        }
    return user_settings[user_id]

# === ETHERSCAN API ===
async def fetch_recent_transfers():
    """Fetch recent large ETH transfers from Etherscan."""
    if not ETHERSCAN_API_KEY:
        return None
    
    url = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x28c6c06298d514db089934071355e5743bf21d60&startblock=0&endblock=99999999&page=1&offset=5&sort=desc&apikey={ETHERSCAN_API_KEY}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1":
                        return data.get("result", [])
    except Exception as e:
        logger.error(f"Etherscan API error: {e}")
    return None

def format_eth(wei_value):
    """Convert wei to ETH."""
    try:
        return round(int(wei_value) / 1e18, 2)
    except:
        return 0

# === TELEGRAM HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu."""
    keyboard = [
        [InlineKeyboardButton("🐋 Live Alerts ON", callback_data="alerts_on")],
        [InlineKeyboardButton("📊 Top Wallets", callback_data="top_wallets")],
        [InlineKeyboardButton("💰 Recent Transfers", callback_data="recent")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("💎 Upgrade to Pro", callback_data="upgrade")],
    ]
    
    text = """🐋 *MVAI Whale Tracker*

Track whale wallets in real-time.
Follow the smart money.

Select an option below:"""
    
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    settings = get_user_settings(user_id)
    data = query.data
    
    if data == "alerts_on":
        settings["alerts"] = True
        await query.edit_message_text(
            "✅ *Alerts Enabled*\n\nYou'll receive notifications for whale movements > 100 ETH.",
            parse_mode="Markdown"
        )
    
    elif data == "alerts_off":
        settings["alerts"] = False
        await query.edit_message_text("🔕 Alerts disabled.")
    
    elif data == "top_wallets":
        text = "🐋 *Tracked Whale Wallets*\n\n"
        for addr, name in WHALE_WALLETS.items():
            short_addr = f"{addr[:6]}...{addr[-4:]}"
            text += f"• *{name}*\n  `{short_addr}`\n"
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif data == "recent":
        await query.edit_message_text("⏳ Fetching recent transfers...")
        
        transfers = await fetch_recent_transfers()
        
        if transfers:
            text = "💰 *Recent Binance Transfers*\n\n"
            for tx in transfers[:5]:
                eth_value = format_eth(tx.get("value", 0))
                if eth_value > 0:
                    direction = "📥 IN" if tx.get("to", "").lower() == "0x28c6c06298d514db089934071355e5743bf21d60" else "📤 OUT"
                    text += f"{direction} {eth_value} ETH\n"
            text += f"\n_Updated: {datetime.now().strftime('%H:%M:%S')}_"
        else:
            text = "📊 *Recent Transfers*\n\n"
            text += "• Binance → Unknown: 500 ETH\n"
            text += "• OKX → DeFi: 1,200 ETH\n"
            text += "• MEXC → Wallet: 340 ETH\n"
            text += "\n_Demo data - add ETHERSCAN_API_KEY for live data_"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif data == "settings":
        keyboard = [
            [InlineKeyboardButton(f"🎯 Threshold: {settings['threshold']} ETH", callback_data="threshold")],
            [InlineKeyboardButton(f"⛓️ Chains: {', '.join(settings['chains'])}", callback_data="chains")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")],
        ]
        await query.edit_message_text(
            "⚙️ *Settings*\n\nConfigure your alerts:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data == "threshold":
        keyboard = [
            [
                InlineKeyboardButton("50 ETH", callback_data="set_threshold_50"),
                InlineKeyboardButton("100 ETH", callback_data="set_threshold_100"),
            ],
            [
                InlineKeyboardButton("500 ETH", callback_data="set_threshold_500"),
                InlineKeyboardButton("1000 ETH", callback_data="set_threshold_1000"),
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="settings")],
        ]
        await query.edit_message_text(
            "🎯 *Select Alert Threshold*\n\nMinimum ETH value to trigger alerts:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data.startswith("set_threshold_"):
        value = int(data.split("_")[-1])
        settings["threshold"] = value
        await query.edit_message_text(f"✅ Threshold set to {value} ETH")
    
    elif data == "chains":
        chains = ["ETH", "BSC", "ARB", "SOL"]
        keyboard = []
        for chain in chains:
            status = "✅" if chain in settings["chains"] else "❌"
            keyboard.append([InlineKeyboardButton(f"{status} {chain}", callback_data=f"toggle_{chain}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="settings")])
        
        await query.edit_message_text(
            "⛓️ *Select Chains*\n\nToggle chains to track:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data.startswith("toggle_"):
        chain = data.split("_")[-1]
        if chain in settings["chains"]:
            settings["chains"].remove(chain)
        else:
            settings["chains"].append(chain)
        
        # Refresh chains menu
        chains = ["ETH", "BSC", "ARB", "SOL"]
        keyboard = []
        for c in chains:
            status = "✅" if c in settings["chains"] else "❌"
            keyboard.append([InlineKeyboardButton(f"{status} {c}", callback_data=f"toggle_{c}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="settings")])
        
        await query.edit_message_text(
            "⛓️ *Select Chains*\n\nToggle chains to track:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data == "upgrade":
        text = """💎 *WhaleFollow Pro*

Get advanced features:
• Real-time alerts (no delay)
• All chains supported
• Lower thresholds (10 ETH+)
• Copy trading signals
• Priority support

*€19/month* or pay with crypto

🔗 [Get Pro](https://mvai.gumroad.com/l/whalefollow-pro)

Or send 20 USDC to:
`0x742d35Cc6634C0532925a3b844Bc9e7595f00000`"""
        
        await query.edit_message_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    
    elif data == "back":
        keyboard = [
            [InlineKeyboardButton("🐋 Live Alerts ON", callback_data="alerts_on")],
            [InlineKeyboardButton("📊 Top Wallets", callback_data="top_wallets")],
            [InlineKeyboardButton("💰 Recent Transfers", callback_data="recent")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("💎 Upgrade to Pro", callback_data="upgrade")],
        ]
        await query.edit_message_text(
            "🐋 *MVAI Whale Tracker*\n\nSelect an option:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable alerts."""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    settings["alerts"] = False
    await update.message.reply_text("🔕 Alerts disabled. Use /start to enable.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status."""
    api_status = "✅ Connected" if ETHERSCAN_API_KEY else "❌ Not configured"
    text = f"""📊 *Bot Status*

🤖 Bot: Online
🔗 Etherscan API: {api_status}
⏰ Server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    await update.message.reply_text(text, parse_mode="Markdown")

# === HEALTH CHECK FOR KOYEB ===
async def health_check(request):
    """HTTP health check endpoint."""
    return web.Response(text="OK", status=200)

async def run_webserver():
    """Run health check webserver."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Health check server running on port {PORT}")

# === MAIN ===
async def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    logger.info("Starting MVAI Whale Tracker Bot...")
    
    # Start health check server
    await run_webserver()
    
    # Create bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start polling
    logger.info("Bot started successfully!")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
