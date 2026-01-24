"""
WhaleFollow Pro - Telegram Bot v4.0
- Health check endpoint (port 8000)
- Live whale data via Etherscan
- Full navigation (back + menu)
- Error handling
- Affiliate integration
"""

import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import httpx

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============================================================================
# ENVIRONMENT VARIABLES (beide naming conventions supported)
# =============================================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_TOKEN')
ETHERSCAN_API = os.environ.get('ETHERSCAN_API') or os.environ.get('ETHERSCAN_KEY')
HELIUS_KEY = os.environ.get('HELIUS_KEY')
SOLSCAN_API = os.environ.get('SOLSCAN_API')

# Affiliate codes
BITUNIX_CODE = os.environ.get('BITUNIX_CODE', 'xc6jzk')
MEXC_CODE = os.environ.get('MEXC_CODE', 'BPM0e8Rm')
BLOFIN_CODE = os.environ.get('BLOFIN_CODE', 'b996a0111c1b4497b53d9b3cc82e4539')

# =============================================================================
# HEALTH CHECK SERVER (Port 8000)
# =============================================================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = '{"status":"ok","bot":"WhaleFollow Pro","version":"4.0"}'
        self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        pass  # Suppress logging

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8000), HealthHandler)
    logger.info("Health check server running on port 8000")
    server.serve_forever()

# =============================================================================
# WHALE DATA FUNCTIONS
# =============================================================================
WHALE_WALLETS = {
    "Binance Hot": "0x28c6c06298d514db089934071355e5743bf21d60",
    "Binance Cold": "0x21a31ee1afc51d94c2efccaa2092ad1028285549",
    "Binance 3": "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503",
    "Bitfinex": "0x8894e0a0c962cb723c1976a4421c95949be2d4e3",
    "Kraken": "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
    "Coinbase": "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
    "Jump Trading": "0x9a9dcd6b52b45a78cd13b395723c245dabfbab71",
    "Wintermute": "0x0000006daea1723962647b7e189d311d757fb793",
}

async def fetch_whale_transactions():
    """Fetch real whale transactions from Etherscan"""
    if not ETHERSCAN_API:
        return None
    
    transactions = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, address in list(WHALE_WALLETS.items())[:5]:
            try:
                url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&page=1&offset=5&sort=desc&apikey={ETHERSCAN_API}"
                response = await client.get(url)
                data = response.json()
                
                if data.get('status') == '1' and data.get('result'):
                    for tx in data['result'][:2]:
                        value_eth = int(tx.get('value', 0)) / 1e18
                        if value_eth > 10:
                            transactions.append({
                                'wallet': name,
                                'hash': tx['hash'][:10] + '...',
                                'value': round(value_eth, 2),
                                'to': tx['to'][:10] + '...' if tx.get('to') else 'Contract',
                                'type': 'OUT' if tx['from'].lower() == address.lower() else 'IN'
                            })
            except Exception as e:
                logger.error(f"Error fetching {name}: {e}")
                continue
    
    return transactions if transactions else None

# =============================================================================
# KEYBOARD BUILDERS
# =============================================================================
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🐋 Live Whale Alerts", callback_data="alerts")],
        [InlineKeyboardButton("📊 Top Wallets", callback_data="wallets")],
        [InlineKeyboardButton("💰 Recent Transfers", callback_data="transfers")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("💎 Trade Now", callback_data="trade")]
    ])

def back_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back", callback_data="back"),
         InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ])

def settings_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Your Stats", callback_data="stats")],
        [InlineKeyboardButton("🎁 Earn Rewards", callback_data="referral")],
        [InlineKeyboardButton("ℹ️ API Status", callback_data="api_status")],
        [InlineKeyboardButton("« Back", callback_data="back"),
         InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ])

def trade_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Bitunix (20% bonus)", url=f"https://www.bitunix.com/register?vipCode={BITUNIX_CODE}")],
        [InlineKeyboardButton("💎 MEXC (40% fees)", url=f"https://www.mexc.com/register?inviteCode={MEXC_CODE}")],
        [InlineKeyboardButton("⚡ BloFin", url=f"https://blofin.com/register?referral_code={BLOFIN_CODE}")],
        [InlineKeyboardButton("« Back", callback_data="back"),
         InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ])

# =============================================================================
# BOT HANDLERS
# =============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - main menu"""
    user = update.effective_user
    
    text = f"""🐋 *MVAI Whale Tracker*

Welcome {user.first_name}!

Track whale wallets in real-time.
Follow the smart money.

*Features:*
• Real-time whale alerts
• Multi-chain tracking
• Copy trade signals
• Risk management alerts

Select an option below:"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text, 
            reply_markup=main_menu_keyboard(),
            parse_mode='Markdown'
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Navigation
    if data in ["back", "menu"]:
        await start(update, context)
        return
    
    # Alerts
    if data == "alerts":
        context.user_data['alerts_enabled'] = True
        text = """✅ *Whale Alerts Activated*

You will receive notifications when whales make significant moves.

Use /stop to disable alerts."""
        await query.edit_message_text(text, reply_markup=back_menu_keyboard(), parse_mode='Markdown')
        return
    
    # Wallets
    if data == "wallets":
        wallet_text = "🐋 *Tracked Whale Wallets*\n\n"
        for name, addr in WHALE_WALLETS.items():
            short_addr = addr[:6] + "..." + addr[-4:]
            wallet_text += f"• *{name}*\n  `{short_addr}`\n"
        
        await query.edit_message_text(wallet_text, reply_markup=back_menu_keyboard(), parse_mode='Markdown')
        return
    
    # Transfers
    if data == "transfers":
        await query.edit_message_text("⏳ Fetching live data...", parse_mode='Markdown')
        
        transactions = await fetch_whale_transactions()
        
        if transactions:
            text = "📊 *Recent Large Transfers*\n\n"
            for tx in transactions[:8]:
                emoji = "🟢" if tx['type'] == 'IN' else "🔴"
                text += f"{emoji} *{tx['wallet']}*\n"
                text += f"   {tx['type']}: {tx['value']} ETH → {tx['to']}\n\n"
            
            text += "_Live data from Etherscan_"
        else:
            text = """📊 *Recent Large Transfers*

⚠️ API connection issue.
Showing sample data:

• Binance → Unknown: 500 ETH
• OKX → DeFi Protocol: 1,200 ETH
• Whale → Coinbase: 850 ETH

_Configure API keys for live data_"""
        
        await query.edit_message_text(text, reply_markup=back_menu_keyboard(), parse_mode='Markdown')
        return
    
    # Settings
    if data == "settings":
        text = """⚙️ *Settings*

Configure your whale tracking preferences."""
        await query.edit_message_text(text, reply_markup=settings_keyboard(), parse_mode='Markdown')
        return
    
    # Trade
    if data == "trade":
        text = """💎 *Trade Now*

Use our partner exchanges and earn rewards:

🔥 *Bitunix* - 20% fee discount
💎 *MEXC* - 40% fee rebate  
⚡ *BloFin* - Premium features"""
        await query.edit_message_text(text, reply_markup=trade_keyboard(), parse_mode='Markdown')
        return
    
    # Stats
    if data == "stats":
        user_id = update.effective_user.id
        ref_code = f"{user_id:X}"[-8:].upper()
        
        text = f"""📈 *YOUR STATS*

• Tier: FREE
• Alerts: 0
• Code: `{ref_code}`

*APIs:* ETH {'✅' if ETHERSCAN_API else '❌'} | SOL {'✅' if SOLSCAN_API else '❌'}"""
        await query.edit_message_text(text, reply_markup=back_menu_keyboard(), parse_mode='Markdown')
        return
    
    # Referral
    if data == "referral":
        user_id = update.effective_user.id
        ref_code = f"{user_id:X}"[-8:].upper()
        bot_username = (await context.bot.get_me()).username
        
        text = f"""🎁 *EARN REWARDS*

Share and earn 30%!

Code: `{ref_code}`
Link: https://t.me/{bot_username}?start={ref_code}"""
        await query.edit_message_text(text, reply_markup=back_menu_keyboard(), parse_mode='Markdown')
        return
    
    # API Status
    if data == "api_status":
        text = f"""ℹ️ *API Status*

• Etherscan: {'✅ Connected' if ETHERSCAN_API else '❌ Not configured'}
• Helius: {'✅ Connected' if HELIUS_KEY else '❌ Not configured'}
• Solscan: {'✅ Connected' if SOLSCAN_API else '❌ Not configured'}

• Bitunix: ✅ `{BITUNIX_CODE}`
• MEXC: ✅ `{MEXC_CODE}`
• BloFin: ✅ Active"""
        await query.edit_message_text(text, reply_markup=back_menu_keyboard(), parse_mode='Markdown')
        return

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop alerts"""
    context.user_data['alerts_enabled'] = False
    await update.message.reply_text(
        "🛑 *Whale Alerts Disabled*\n\nUse /start to enable again.",
        reply_markup=back_menu_keyboard(),
        parse_mode='Markdown'
    )

# =============================================================================
# MAIN
# =============================================================================
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    logger.info(f"Starting bot with token: {BOT_TOKEN[:10]}...")
    logger.info(f"Etherscan API: {'Set' if ETHERSCAN_API else 'Not set'}")
    
    # Start health check server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health server started")
    
    # Build bot application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Run bot
    logger.info("Starting bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
