import os, logging, asyncio, aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_KEY", os.environ.get("ETHERSCAN_API", ""))
PORT = int(os.environ.get("PORT", 8000))
ADMIN_IDS = [int(os.environ.get("ADMIN_ID", "0"))]
PRO_PRICE = "€19/month"
GUMROAD_LINK = "https://mvai.gumroad.com/l/whalefollow-pro"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args): pass

def run_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

WHALE_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Cold",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "Binance Whale",
    "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance 8",
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3": "Bitfinex",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX",
}

user_settings = {}
user_subscriptions = {}
pro_users = set()

def is_admin(user_id): return user_id in ADMIN_IDS and user_id != 0
def has_pro(user_id): return is_admin(user_id) or user_id in pro_users
def back_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="menu")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"threshold": 100, "chains": ["ETH"]}
    
    badge = " 👑" if is_admin(user_id) else (" ⭐" if has_pro(user_id) else "")
    
    keyboard = [
        [InlineKeyboardButton("🐋 Live Alerts ON", callback_data="alerts")],
        [InlineKeyboardButton("📊 Top Wallets", callback_data="smart_wallets")],
        [InlineKeyboardButton("💰 Recent Transfers", callback_data="recent")],
        [InlineKeyboardButton("🔍 Find Smart Wallets", callback_data="find_wallets")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("💎 Upgrade to Pro", callback_data="pro")],
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    
    await update.message.reply_text(
        f"🐋 *WhaleFollow Pro*{badge}\n\nTrack whale wallets in real-time.\nFollow the smart money.\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data
    
    if user_id not in user_settings:
        user_settings[user_id] = {"threshold": 100, "chains": ["ETH"]}
    
    if data == "menu":
        badge = " 👑" if is_admin(user_id) else (" ⭐" if has_pro(user_id) else "")
        keyboard = [
            [InlineKeyboardButton("🐋 Live Alerts ON", callback_data="alerts")],
            [InlineKeyboardButton("📊 Top Wallets", callback_data="smart_wallets")],
            [InlineKeyboardButton("💰 Recent Transfers", callback_data="recent")],
            [InlineKeyboardButton("🔍 Find Smart Wallets", callback_data="find_wallets")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("💎 Upgrade to Pro", callback_data="pro")],
        ]
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
        await q.edit_message_text(f"🐋 *WhaleFollow Pro*{badge}\n\nSelect an option:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "alerts":
        user_subscriptions[user_id] = True
        await q.edit_message_text(f"✅ *Alerts Active*\n\nThreshold: {user_settings[user_id]['threshold']} ETH\nChains: {', '.join(user_settings[user_id]['chains'])}", reply_markup=back_kb(), parse_mode="Markdown")
    
    elif data == "smart_wallets" or data == "find_wallets":
        text = "📊 *Top Whale Wallets*\n\n"
        for addr, name in list(WHALE_WALLETS.items())[:5]:
            text += f"• *{name}*\n  `{addr[:8]}...{addr[-4:]}`\n\n"
        await q.edit_message_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    
    elif data == "recent":
        await q.edit_message_text("🔄 *Loading...*", parse_mode="Markdown")
        text = await fetch_transfers()
        await q.edit_message_text(text, reply_markup=back_kb(), parse_mode="Markdown")
    
    elif data == "settings":
        keyboard = [
            [InlineKeyboardButton("🔔 Threshold", callback_data="threshold")],
            [InlineKeyboardButton("⛓️ Chains", callback_data="chains")],
            [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
        ]
        await q.edit_message_text(f"⚙️ *Settings*\n\nThreshold: *{user_settings[user_id]['threshold']} ETH*\nChains: *{', '.join(user_settings[user_id]['chains'])}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "threshold":
        keyboard = [
            [InlineKeyboardButton("50", callback_data="t_50"), InlineKeyboardButton("100", callback_data="t_100")],
            [InlineKeyboardButton("500", callback_data="t_500"), InlineKeyboardButton("1000", callback_data="t_1000")],
            [InlineKeyboardButton("🔙 Back", callback_data="settings")],
        ]
        await q.edit_message_text(f"🔔 *Threshold*\n\nCurrent: *{user_settings[user_id]['threshold']} ETH*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data.startswith("t_"):
        user_settings[user_id]["threshold"] = int(data[2:])
        await q.edit_message_text(f"✅ Threshold set to *{data[2:]} ETH*", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Settings", callback_data="settings")]]), parse_mode="Markdown")
    
    elif data == "chains":
        current = user_settings[user_id]["chains"]
        keyboard = [[InlineKeyboardButton(f"{'✅' if c in current else '⬜'} {c}", callback_data=f"c_{c}")] for c in ["ETH","BSC","ARB","SOL"]]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="settings")])
        await q.edit_message_text(f"⛓️ *Chains*\n\nActive: *{', '.join(current)}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data.startswith("c_"):
        chain = data[2:]
        current = user_settings[user_id]["chains"]
        if chain in current and len(current) > 1:
            current.remove(chain)
        elif chain not in current:
            current.append(chain)
        keyboard = [[InlineKeyboardButton(f"{'✅' if c in current else '⬜'} {c}", callback_data=f"c_{c}")] for c in ["ETH","BSC","ARB","SOL"]]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="settings")])
        await q.edit_message_text(f"⛓️ *Chains*\n\nActive: *{', '.join(current)}*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "pro":
        keyboard = [
            [InlineKeyboardButton("💳 Pay with Card", url=GUMROAD_LINK)],
            [InlineKeyboardButton("₿ Pay with Crypto", callback_data="crypto")],
            [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
        ]
        await q.edit_message_text(f"💎 *WhaleFollow Pro*\n\n*{PRO_PRICE}* - pay what you want\n\n✓ Unlimited alerts\n✓ All chains\n✓ Smart wallets\n✓ Copy signals (soon)\n\nSelect payment:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "crypto":
        await q.edit_message_text("₿ *Crypto Payment*\n\nContact @MVAI\\_Support for crypto payment details.", reply_markup=back_kb(), parse_mode="Markdown")
    
    elif data == "admin" and is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("📊 Stats", callback_data="a_stats")],
            [InlineKeyboardButton("➕ Add Pro User", callback_data="a_addpro")],
            [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
        ]
        await q.edit_message_text(f"👑 *Admin Panel*\n\nUsers: {len(user_settings)}\nActive alerts: {sum(1 for v in user_subscriptions.values() if v)}\nPro users: {len(pro_users)}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "a_stats" and is_admin(user_id):
        await q.edit_message_text(f"📊 *Stats*\n\nUsers: {len(user_settings)}\nPro: {len(pro_users)}\nAlerts: {sum(1 for v in user_subscriptions.values() if v)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data="admin")]]), parse_mode="Markdown")
    
    elif data == "a_addpro" and is_admin(user_id):
        await q.edit_message_text("➕ *Add Pro User*\n\nUse command:\n`/addpro USER_ID`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data="admin")]]), parse_mode="Markdown")

async def fetch_transfers():
    if not ETHERSCAN_API_KEY:
        return "⚠️ API not configured"
    try:
        wallet = list(WHALE_WALLETS.keys())[0]
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet}&page=1&offset=5&sort=desc&apikey={ETHERSCAN_API_KEY}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                data = await r.json()
        if data["status"] == "1":
            text = "💰 *Recent Transfers*\n\n"
            for tx in data["result"][:5]:
                eth = int(tx["value"]) / 10**18
                if eth > 0:
                    text += f"• *{eth:.2f} ETH*\n  [View](https://etherscan.io/tx/{tx['hash']})\n\n"
            return text
        return "No transfers found"
    except Exception as e:
        return f"⚠️ Error: {e}"

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_subscriptions[update.effective_user.id] = False
    await update.message.reply_text("🔕 Alerts off. /start to enable.")

async def addpro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.args:
        pro_users.add(int(context.args[0]))
        await update.message.reply_text(f"✅ Pro added: {context.args[0]}")

async def main():
    if not BOT_TOKEN:
        logger.error("NO BOT_TOKEN")
        return
    Thread(target=run_health_server, daemon=True).start()
    logger.info(f"Health server on port {PORT}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("addpro", addpro))
    app.add_handler(CallbackQueryHandler(button))
    
    logger.info("Bot started!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
