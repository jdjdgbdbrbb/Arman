# Arman VIP Income Bot

Telegram bot + Telegram Mini App starter project. It includes:
- Telegram Mini App with video task list and minimum watch timer.
- Reward credited once per user per video.
- One-time 2 BDT group-join reward with Telegram membership verification.
- Balance and manual withdrawal request.
- Admin commands to add videos and view basic stats.
- Separate ad configuration placeholders (`ads.py`, `ads_config.js`).

## Important limitations
- The watch timer only enforces elapsed time. It cannot prove a person watched every frame or prevent all browser manipulation.
- Withdrawals are requests for manual admin payment. No bKash/Nagad API is connected.
- VIP is currently an information/request placeholder; no paid membership or payment gateway is connected.
- Ads are disabled until you add an approved provider's official script and IDs. Do not paste random scripts.
- This is a starter implementation, not a guarantee of earnings. Only promise rewards you can actually fund.

## Setup
1. Create a Telegram bot with @BotFather. If an old token was ever committed to a public GitHub repository, revoke it and generate a new token.
2. Copy `.env.example` to `.env` and fill `BOT_TOKEN`, `BOT_USERNAME`, and your deployed HTTPS `WEBAPP_URL`.
3. Keep `.env` private. Never upload it to GitHub.
4. Add the bot to `@DigitalIncomeZone912` as an administrator with permission to view members.
5. Install dependencies: `pip install -r requirements.txt`
6. Run: `python main.py`
7. In Telegram, send `/addvideo Title | https://example.com/video | 2 | 30` as the admin.
8. Send `/start` to the bot and open the Web App button.

## Admin
- Telegram numeric admin ID: `6577841902`
- Username label: `@ItsArman36`
- `/addvideo Title | URL | Reward | Minimum_Seconds`
- `/stats`

## Deployment
Deploy on a Python host that supports a persistent process and persistent disk for SQLite. Set environment variables from `.env.example`. Set `WEBAPP_URL` to the app's public HTTPS URL. A free ephemeral filesystem may erase the database on restart.

## Ad placement
Edit `ads.py` and `ads_config.js` only after selecting an ad provider that permits your app's traffic type. Add the provider's official integration code and IDs to the marked fields. Ad network approval may be required.
