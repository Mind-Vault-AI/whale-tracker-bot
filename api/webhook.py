from http.server import BaseHTTPRequestHandler
import json, os, urllib.request, urllib.parse

BOT_TOKEN = os.environ.get('BOT_TOKEN')
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

WALLETS = {
    "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance Hot",
    "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549": "Binance Cold",
    "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d": "Bitfinex",
    "0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0": "Coinbase Prime",
    "0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b": "OKX Hot"
}

def send(chat_id, text):
    data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}).encode()
    urllib.request.urlopen(f"{API}/sendMessage", data)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if 'message' in body:
            msg = body['message']
            cid, txt = msg['chat']['id'], msg.get('text','')
            if txt == '/start': send(cid, "🐋 *WhaleFollow Pro*\n\n/wallets - Bekijk wallets\n/info - Info")
            elif txt == '/wallets': send(cid, "🐋 *Wallets:*\n" + "\n".join([f"• {n}: `{a[:8]}...`" for a,n in WALLETS.items()]))
            elif txt == '/info': send(cid, "🐋 WhaleFollow Pro v1.0\n\nSupport: @mindvaultai")
        self.send_response(200)
        self.end_headers()
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')