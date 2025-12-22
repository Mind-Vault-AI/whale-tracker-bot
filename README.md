# MVAI Whale Tracker Bot

Telegram: @MVAi_WhalesTrader_Bot

## Koyeb Deployment (Mobile)

### Step 1: GitHub Setup
Upload these 3 files to your `whale-tracker-bot` repo:
- `bot.py`
- `requirements.txt`
- `Procfile`

### Step 2: Get Bot Token
1. Open Telegram → @BotFather
2. Send `/mybots`
3. Select @MVAi_WhalesTrader_Bot
4. Click "API Token" → Copy it

### Step 3: Koyeb Deployment
1. Go to https://app.koyeb.com
2. Sign up (no credit card needed)
3. Click "Create App"
4. Select "GitHub"
5. Connect your GitHub account
6. Select `whale-tracker-bot` repository
7. Set environment variables:
   - `BOT_TOKEN` = your telegram bot token
   - `ETHERSCAN_API_KEY` = (optional, get free at etherscan.io)
8. Click "Deploy"

### Step 4: Verify
1. Open Telegram
2. Go to @MVAi_WhalesTrader_Bot
3. Send `/start`
4. Bot should respond with menu

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| BOT_TOKEN | Yes | Telegram bot token from @BotFather |
| ETHERSCAN_API_KEY | No | Free API key from etherscan.io |

## Commands

- `/start` - Main menu
- `/stop` - Disable alerts
- `/status` - Bot status

## Free Tier Limits (Koyeb)

- 512MB RAM
- 0.1 vCPU
- Supports ~200-300 users
- No credit card required
