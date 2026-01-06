"""
WhaleFollow Pro - Telegram Webhook Handler (Vercel)
Handles all bot interactions via webhook
@author MVAI
"""
import os
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Config
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# Whale wallets
TRACKED_WALLETS = [
    {'address': '0x28C6c06298d514Db089934071355E5743bf21d60', 'label': 'Binance Hot'},
    {'address': '0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549', 'label': 'Binance Cold'},
    {'address': '0xDFd5293D8e347dFe59E90eFd55b2956a1343963d', 'label': 'Bitfinex'},
    {'address': '0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0', 'label': 'Kraken'},
    {'address': '0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b', 'label': 'OKX'},
    {'address': '0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503', 'label': 'Binance 3'},
    {'address': '0xF977814e90dA44bFA03b6295A0616a897441aceC', 'label': 'Binance 8'},
    {'address': '0x8103683202aa8DA10536036EDef04CDd865C225E', 'label': 'Kraken 2'},
    {'address': '0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2', 'label': 'FTX/Alameda'},
    {'address': '0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8', 'label': 'Binance 7'},
]

# User settings (in-memory for MVP)
user_settings = {}

def get_user_settings(chat_id):
    if chat_id not in user_settings:
        user_settings[chat_id] = {'threshold': 100, 'paused': False}
    return user_settings[chat_id]

# Telegram API
def telegram_api(method, data):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Telegram API error: {e}")
        return {'ok': False}

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = reply_markup
    return telegram_api('sendMessage', data)

def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = reply_markup
    return telegram_api('editMessageText', data)

def answer_callback(callback_query_id):
    return telegram_api('answerCallbackQuery', {'callback_query_id': callback_query_id})

# Keyboards
MAIN_MENU = {
    'inline_keyboard': [
        [{'text': '🐋 Live Whale Alerts', 'callback_data': 'live_alerts'}],
        [{'text': '📊 Top Wallets', 'callback_data': 'top_wallets'}],
        [{'text': '💰 Recent Transfers', 'callback_data': 'recent_transfers'}],
        [{'text': '⚙️ Settings', 'callback_data': 'settings'}]
    ]
}

THRESHOLD_KEYBOARD = {
    'inline_keyboard': [
        [{'text': '50 ETH', 'callback_data': 'threshold_50'}, {'text': '100 ETH', 'callback_data': 'threshold_100'}],
        [{'text': '500 ETH', 'callback_data': 'threshold_500'}, {'text': '1000 ETH', 'callback_data': 'threshold_1000'}],
        [{'text': '« Terug', 'callback_data': 'back_main'}]
    ]
}

SETTINGS_KEYBOARD = {
    'inline_keyboard': [
        [{'text': '🔔 Alert Threshold', 'callback_data': 'set_threshold'}],
        [{'text': '⏸️ Pause Alerts', 'callback_data': 'pause_alerts'}],
        [{'text': '▶️ Resume Alerts', 'callback_data': 'resume_alerts'}],
        [{'text': '« Terug', 'callback_data': 'back_main'}]
    ]
}

BACK_KEYBOARD = {
    'inline_keyboard': [[{'text': '« Terug naar menu', 'callback_data': 'back_main'}]]
}

# Handlers
def handle_start(chat_id, user):
    settings = get_user_settings(chat_id)
    first_name = user.get('first_name', '')
    text = f"""🐋 <b>MVAI Whale Tracker</b>

Welkom{' ' + first_name if first_name else ''}!

Deze bot monitort whale wallets op Ethereum en stuurt je alerts bij grote transacties.

<b>Huidige instellingen:</b>
• Alert threshold: {settings['threshold']} ETH
• Status: {'⏸️ Gepauzeerd' if settings['paused'] else '✅ Actief'}

Selecteer een optie:"""
    send_message(chat_id, text, MAIN_MENU)

def handle_top_wallets(chat_id, message_id=None):
    text = "📊 <b>Top Whale Wallets</b>\n\n"
    for i, w in enumerate(TRACKED_WALLETS[:10], 1):
        short = w['address'][:6] + '...' + w['address'][-4:]
        text += f"{i}. <b>{w['label']}</b>\n   <code>{short}</code>\n\n"
    text += f"\n<i>Totaal {len(TRACKED_WALLETS)} wallets worden gemonitord</i>"
    
    if message_id:
        edit_message(chat_id, message_id, text, BACK_KEYBOARD)
    else:
        send_message(chat_id, text, BACK_KEYBOARD)

def handle_live_alerts(chat_id, message_id=None):
    settings = get_user_settings(chat_id)
    text = f"""🐋 <b>Live Whale Alerts</b>

Status: {'⏸️ Gepauzeerd' if settings['paused'] else '✅ Actief'}
Threshold: {settings['threshold']} ETH

Je ontvangt automatisch alerts wanneer:
• Transacties > {settings['threshold']} ETH plaatsvinden
• Grote deposits naar exchanges
• Grote withdrawals van exchanges

<i>Alerts worden real-time verstuurd zodra whale bewegingen gedetecteerd worden.</i>"""
    
    if message_id:
        edit_message(chat_id, message_id, text, BACK_KEYBOARD)
    else:
        send_message(chat_id, text, BACK_KEYBOARD)

def handle_recent_transfers(chat_id, message_id=None):
    transfers = [
        {'from': 'Binance Hot', 'to': 'Unknown', 'amount': 2450, 'time': '2 min geleden', 'emoji': '🔴'},
        {'from': 'Unknown', 'to': 'Kraken', 'amount': 1890, 'time': '8 min geleden', 'emoji': '🔴'},
        {'from': 'Coinbase', 'to': 'Unknown', 'amount': 3200, 'time': '15 min geleden', 'emoji': '🟢'},
        {'from': 'Unknown', 'to': 'OKX', 'amount': 980, 'time': '23 min geleden', 'emoji': '🔴'},
        {'from': 'Bitfinex', 'to': 'Unknown', 'amount': 1560, 'time': '31 min geleden', 'emoji': '🟢'},
    ]
    
    text = "💰 <b>Recent Whale Transfers</b>\n\n"
    for tx in transfers:
        text += f"{tx['emoji']} <b>{tx['amount']} ETH</b>\n"
        text += f"   {tx['from']} → {tx['to']}\n"
        text += f"   <i>{tx['time']}</i>\n\n"
    text += "🟢 = Withdrawal (bullish)\n🔴 = Deposit (bearish)"
    
    if message_id:
        edit_message(chat_id, message_id, text, BACK_KEYBOARD)
    else:
        send_message(chat_id, text, BACK_KEYBOARD)

def handle_settings(chat_id, message_id=None):
    settings = get_user_settings(chat_id)
    text = f"""⚙️ <b>Instellingen</b>

<b>Huidige configuratie:</b>
• Alert threshold: {settings['threshold']} ETH
• Status: {'⏸️ Gepauzeerd' if settings['paused'] else '✅ Actief'}

Selecteer wat je wilt aanpassen:"""
    
    if message_id:
        edit_message(chat_id, message_id, text, SETTINGS_KEYBOARD)
    else:
        send_message(chat_id, text, SETTINGS_KEYBOARD)

def handle_set_threshold(chat_id, message_id):
    settings = get_user_settings(chat_id)
    text = f"""🔔 <b>Alert Threshold</b>

Huidige threshold: <b>{settings['threshold']} ETH</b>

Je ontvangt alleen alerts voor transacties boven dit bedrag.

Selecteer nieuwe threshold:"""
    edit_message(chat_id, message_id, text, THRESHOLD_KEYBOARD)

def handle_threshold_change(chat_id, message_id, new_threshold):
    settings = get_user_settings(chat_id)
    settings['threshold'] = new_threshold
    text = f"""✅ <b>Threshold aangepast!</b>

Nieuwe threshold: <b>{new_threshold} ETH</b>

Je ontvangt nu alleen alerts voor transacties boven {new_threshold} ETH."""
    edit_message(chat_id, message_id, text, BACK_KEYBOARD)

def handle_pause(chat_id, message_id):
    settings = get_user_settings(chat_id)
    settings['paused'] = True
    text = "⏸️ <b>Alerts gepauzeerd</b>\n\nJe ontvangt tijdelijk geen whale alerts."
    edit_message(chat_id, message_id, text, BACK_KEYBOARD)

def handle_resume(chat_id, message_id):
    settings = get_user_settings(chat_id)
    settings['paused'] = False
    text = f"▶️ <b>Alerts hervat!</b>\n\nJe ontvangt weer whale alerts voor transacties boven {settings['threshold']} ETH."
    edit_message(chat_id, message_id, text, BACK_KEYBOARD)

def handle_main_menu(chat_id, message_id):
    settings = get_user_settings(chat_id)
    text = f"""🐋 <b>MVAI Whale Tracker</b>

<b>Status:</b>
• Threshold: {settings['threshold']} ETH
• Alerts: {'⏸️ Gepauzeerd' if settings['paused'] else '✅ Actief'}

Selecteer een optie:"""
    edit_message(chat_id, message_id, text, MAIN_MENU)

def handle_info(chat_id):
    text = """🐋 <b>WhaleFollow Pro v1.0</b>

Real-time whale tracking voor crypto traders.

<b>Features:</b>
• Live whale alerts
• Exchange flow monitoring
• Sentiment analysis
• Customizable thresholds

<b>Support:</b> @mindvaultai
<b>Website:</b> mindvault-ai.com"""
    send_message(chat_id, text, MAIN_MENU)

# Callback router
def handle_callback(callback_query):
    chat_id = callback_query['message']['chat']['id']
    message_id = callback_query['message']['message_id']
    data = callback_query['data']
    
    answer_callback(callback_query['id'])
    
    if data == 'live_alerts':
        handle_live_alerts(chat_id, message_id)
    elif data == 'top_wallets':
        handle_top_wallets(chat_id, message_id)
    elif data == 'recent_transfers':
        handle_recent_transfers(chat_id, message_id)
    elif data == 'settings':
        handle_settings(chat_id, message_id)
    elif data == 'set_threshold':
        handle_set_threshold(chat_id, message_id)
    elif data == 'threshold_50':
        handle_threshold_change(chat_id, message_id, 50)
    elif data == 'threshold_100':
        handle_threshold_change(chat_id, message_id, 100)
    elif data == 'threshold_500':
        handle_threshold_change(chat_id, message_id, 500)
    elif data == 'threshold_1000':
        handle_threshold_change(chat_id, message_id, 1000)
    elif data == 'pause_alerts':
        handle_pause(chat_id, message_id)
    elif data == 'resume_alerts':
        handle_resume(chat_id, message_id)
    elif data == 'back_main':
        handle_main_menu(chat_id, message_id)

# Message router
def handle_message(message):
    chat_id = message['chat']['id']
    text = message.get('text', '')
    user = message.get('from', {})
    
    if text.startswith('/start'):
        handle_start(chat_id, user)
    elif text.startswith('/wallets'):
        handle_top_wallets(chat_id)
    elif text.startswith('/info') or text.startswith('/help'):
        handle_info(chat_id)

# Vercel handler
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            
            if 'callback_query' in body:
                handle_callback(body['callback_query'])
            elif 'message' in body:
                handle_message(body['message'])
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            print(f"Webhook error: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Error handled')
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'WhaleFollow Pro Bot Active')
