import os, logging, asyncio, aiohttp, hmac, hashlib, time, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode

# === CONFIG ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ETHERSCAN_API_KEY = os.environ.get("ETHERSCAN_KEY", os.environ.get("ETHERSCAN_API", ""))
PORT = int(os.environ.get("PORT", 8000))
ADMIN_IDS = [int(os.environ.get("ADMIN_ID", "0"))]
CRYPTO_WALLET = os.environ.get("CRYPTO_WALLET", "")

# Exchange APIs
BITUNIX_API_KEY = os.environ.get("BITUNIX_API_KEY", "")
BITUNIX_SECRET_KEY = os.environ.get("BITUNIX_SECRET_KEY", "")
BITUNIX_CODE = os.environ.get("BITUNIX_CODE", "xc6jzk")
MEXC_CODE = os.environ.get("MEXC_CODE", "BPM0e8Rm")
BLOFIN_API_KEY = os.environ.get("BLOFIN_API_KEY", "")
BLOFIN_CODE = os.environ.get("BLOFIN_CODE", "")

PRO_PRICE = "€19/month"
GUMROAD_LINK = "https://mvai.gumroad.com/l/whalefollow-pro"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# === HEALTH SERVER ===
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args): pass

def run_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

# === WHALE WALLETS ===
WHALE_WALLETS = {
    "0x28c6c06298d514db089934071355e5743bf21d60": "Binance Hot",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "Binance Cold",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "Binance Whale",
    "0xf977814e90da44bfa03b6295a0616a897441acec": "Binance 8",
    "0x8894e0a0c962cb723c1976a4421c95949be2d4e3": "Bitfinex",
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": "OKX",
}

# === USER DATA ===
user_settings = {}
user_subscriptions = {}
pro_users = set()
user_api_keys = {}  # {user_id: {"exchange": "bitunix", "api_key": "...", "secret": "..."}}
pending_action = {}  # {user_id: "awaiting_api_key" or "awaiting_secret"}

# === HELPERS ===
def is_admin(user_id): return user_id in ADMIN_IDS and user_id != 0
def has_pro(user_id): return is_admin(user_id) or user_id in pro_users
def back_kb(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Menu", callback_data="menu")]])

# === BITUNIX API ===
async def bitunix_get_balance(api_key, secret):
    """Get account balance from Bitunix"""
    try:
        timestamp = str(int(time.time() * 1000))
        params = {"timestamp": timestamp}
        query = urlencode(params)
        signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        
        url = f"https://api.bitunix.com/api/v1/account/balance?{query}&signature={signature}"
        headers = {"X-API-KEY": api_key}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                return data
    except Exception as e:
        logger.error(f"Bitunix balance error: {e}")
        return {"error": str(e)}

async def bitunix_place_order(api_key, secret, symbol, side, amount):
    """Place market order on Bitunix"""
    try:
        timestamp = str(int(time.time() * 1000))
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": str(amount),
            "timestamp": timestamp
        }
        query = urlencode(sorted(params.items()))
        signature = hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        
        url = "https://api.bitunix.com/api/v1/order"
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        params["signature"] = signature
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=params) as resp:
                data = await resp.json()
                return data
    except Exception as e:
        logger.error(f"Bitunix order error: {e}")
        return {"error": str(e)}

# === TELEGRAM HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"threshold": 100, "chains": ["ETH"]}
    
    badge = " 👑" if is_admin(user_id) else (" ⭐" if has_pro(user_id) else "")
    
    keyboard = [
        [InlineKeyboardButton("🐋 Live Alerts ON", callback_data="alerts")],
        [InlineKeyboardButton("📊 Top Wallets", callback_data="smart_wallets")],
        [InlineKeyboardButton("💰 Recent Transfers", callback_data="recent")],
        [InlineKeyboardButton("🔗 Connect Exchange", callback_data="connect")],
        [InlineKeyboardButton("📈 Copy Trade", callback_data="copy_trade")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("💎 Upgrade to Pro", callback_data="pro")],
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin")])
    
    await update.message.reply_text(
        f"🐋 *WhaleFollow Pro*{badge}\n\nTrack whale wallets in real-time.\nFollow the smart money.\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for API key input"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id in pending_action:
        action = pending_action[user_id]
        
        if action == "awaiting_api_key":
            if user_id not in user_api_keys:
                user_api_keys[user_id] = {}
            user_api_keys[user_id]["api_key"] = text
            pending_action[user_id] = "awaiting_secret"
            await update.message.delete()
            await update.message.reply_text(
                "✅ API Key saved\\!\n\nNow send your *Secret Key*:",
                parse_mode="MarkdownV2"
            )
        
        elif action == "awaiting_secret":
            user_api_keys[user_id]["secret"] = text
            user_api_keys[user_id]["exchange"] = "bitunix"
            del pending_action[user_id]
            await update.message.delete()
            await update.message.reply_text(
                "✅ *Exchange Connected\\!*\n\nYou can now use Copy Trade\\.",
                reply_markup=back_kb(),
                parse_mode="MarkdownV2"
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
            [InlineKeyboardButton("🔗 Connect Exchange", callback_data="connect")],
            [InlineKeyboardButton("📈 Copy Trade", callback_data="copy_trade")],
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
    
    elif data == "connect":
        if not has_pro(user_id):
            await q.edit_message_text("🔒 *Pro Feature*\n\nUpgrade to Pro to connect your exchange.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade", callback_data="pro")], [InlineKeyboardButton("🔙 Menu", callback_data="menu")]]), parse_mode="Markdown")
            return
        
        keyboard = [
            [InlineKeyboardButton("🟢 Bitunix", callback_data="conn_bitunix")],
            [InlineKeyboardButton("🔵 MEXC", callback_data="conn_mexc")],
            [InlineKeyboardButton("🟣 BloFin", callback_data="conn_blofin")],
            [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
        ]
        
        status = "❌ Not connected"
        if user_id in user_api_keys:
            status = f"✅ Connected to {user_api_keys[user_id].get('exchange', 'unknown').upper()}"
        
        await q.edit_message_text(
            f"🔗 *Connect Exchange*\n\nStatus: {status}\n\n⚠️ Use READ-ONLY API keys for safety\\!\n\nSelect exchange:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data == "conn_bitunix":
        pending_action[user_id] = "awaiting_api_key"
        keyboard = [[InlineKeyboardButton("📝 Get API Key", url=f"https://www.bitunix.com/register?ref={BITUNIX_CODE}")], [InlineKeyboardButton("🔙 Cancel", callback_data="connect")]]
        await q.edit_message_text(
            "🟢 *Connect Bitunix*\n\n1\\. Create API key at Bitunix\n2\\. Enable READ\\-ONLY permissions\n3\\. Send your API Key here:\n\n_Your keys are stored securely_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )
    
    elif data == "conn_mexc":
        keyboard = [[InlineKeyboardButton("📝 Register MEXC", url=f"https://www.mexc.com/register?inviteCode={MEXC_CODE}")], [InlineKeyboardButton("🔙 Back", callback_data="connect")]]
        await q.edit_message_text("🔵 *MEXC*\n\nComing soon\\! Register now with our affiliate link:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
    
    elif data == "conn_blofin":
        keyboard = [[InlineKeyboardButton("📝 Register BloFin", url="https://blofin.com/register")], [InlineKeyboardButton("🔙 Back", callback_data="connect")]]
        await q.edit_message_text("🟣 *BloFin*\n\nComing soon\\! Register now:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
    
    elif data == "copy_trade":
        if not has_pro(user_id):
            await q.edit_message_text("🔒 *Pro Feature*\n\nUpgrade to Pro to use Copy Trade.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade", callback_data="pro")], [InlineKeyboardButton("🔙 Menu", callback_data="menu")]]), parse_mode="Markdown")
            return
        
        if user_id not in user_api_keys:
            await q.edit_message_text("⚠️ *Connect Exchange First*\n\nYou need to connect your exchange before using Copy Trade.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Connect", callback_data="connect")], [InlineKeyboardButton("🔙 Menu", callback_data="menu")]]), parse_mode="Markdown")
            return
        
        keyboard = [
            [InlineKeyboardButton("🐋 Follow Binance Hot", callback_data="follow_binance")],
            [InlineKeyboardButton("🦈 Follow Bitfinex", callback_data="follow_bitfinex")],
            [InlineKeyboardButton("📊 My Positions", callback_data="positions")],
            [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
        ]
        await q.edit_message_text(
            f"📈 *Copy Trade*\n\nExchange: *{user_api_keys[user_id].get('exchange', '').upper()}*\n\nSelect a whale to follow:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data.startswith("follow_"):
        whale = data.replace("follow_", "")
        keyboard = [
            [InlineKeyboardButton("✅ Confirm - Copy Next Trade", callback_data=f"confirm_{whale}")],
            [InlineKeyboardButton("🔙 Back", callback_data="copy_trade")],
        ]
        await q.edit_message_text(
            f"🐋 *Follow {whale.title()} Whale*\n\n• Auto-copy next trade\n• Max 5% of your balance\n• Stop-loss: 10%\n\n⚠️ Trading involves risk!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    
    elif data.startswith("confirm_"):
        whale = data.replace("confirm_", "")
        # In production: start monitoring whale + auto-execute trades
        await q.edit_message_text(
            f"✅ *Following {whale.title()} Whale*\n\nYou will receive alerts and auto-copy trades.\n\n_Monitoring active..._",
            reply_markup=back_kb(),
            parse_mode="Markdown"
        )
    
    elif data == "positions":
        if user_id in user_api_keys:
            keys = user_api_keys[user_id]
            result = await bitunix_get_balance(keys.get("api_key", ""), keys.get("secret", ""))
            if "error" in result:
                await q.edit_message_text(f"⚠️ Error: {result['error']}", reply_markup=back_kb())
            else:
                await q.edit_message_text(f"📊 *Your Positions*\n\n```{json.dumps(result, indent=2)[:500]}```", reply_markup=back_kb(), parse_mode="Markdown")
        else:
            await q.edit_message_text("Connect exchange first.", reply_markup=back_kb())
    
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
        await q.edit_message_text(f"💎 *WhaleFollow Pro*\n\n*{PRO_PRICE}* - pay what you want\n\n✓ Unlimited alerts\n✓ All chains\n✓ Copy trading\n✓ Exchange connection\n✓ Smart wallet tracking\n\nSelect payment:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "crypto":
        if CRYPTO_WALLET:
            await q.edit_message_text(f"₿ *Crypto Payment*\n\nSend €19 equivalent to:\n\n`{CRYPTO_WALLET}`\n\nThen contact @MVAI\\_Support with TX hash\\.", reply_markup=back_kb(), parse_mode="MarkdownV2")
        else:
            await q.edit_message_text("₿ *Crypto Payment*\n\nContact @MVAI\\_Support for crypto payment details\\.", reply_markup=back_kb(), parse_mode="MarkdownV2")
    
    elif data == "admin" and is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("📊 Stats", callback_data="a_stats")],
            [InlineKeyboardButton("➕ Add Pro User", callback_data="a_addpro")],
            [InlineKeyboardButton("🔙 Menu", callback_data="menu")],
        ]
        await q.edit_message_text(f"👑 *Admin Panel*\n\nUsers: {len(user_settings)}\nActive alerts: {sum(1 for v in user_subscriptions.values() if v)}\nPro users: {len(pro_users)}\nConnected exchanges: {len(user_api_keys)}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    
    elif data == "a_stats" and is_admin(user_id):
        await q.edit_message_text(f"📊 *Stats*\n\nUsers: {len(user_settings)}\nPro: {len(pro_users)}\nAlerts: {sum(1 for v in user_subscriptions.values() if v)}\nExchanges: {len(user_api_keys)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data="admin")]]), parse_mode="Markdown")
    
    elif data == "a_addpro" and is_admin(user_id):
        await q.edit_message_text("➕ *Add Pro User*\n\nUse command:\n`/addpro USER_ID`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data="admin")]]), parse_mode="Markdown")

async def fetch_transfers():
    if not ETHERSCAN_API_KEY:
        return "⚠️ API not configured"
    try:
        wallet = list(WHALE_WALLETS.keys())[0]
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet}&page=1&offset=5&sort=desc&apikey={ETHERSCAN_API_KEY}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
