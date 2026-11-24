# First bot

Telegram earning/reward bot starter project. It awards points for referrals and admin-approved tasks. Withdrawals are requests for manual review; the bot does not send money automatically.

## Files
- `bot.py` — Telegram bot backend
- `requirements.txt` — Python dependency
- `.env.example` — blank token/config template
- `index.html` — simple landing page
- `Pic1.svg` — profile-picture placeholder
- `Pic2.svg` — cover-picture placeholder

## Setup
1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Open `bot.py` and put the token between the quotes in `BOT_TOKEN = ""`, or set the `BOT_TOKEN` environment variable. Never publish your real token in a public repository.
3. Set `ADMIN_ID` to your numeric Telegram user ID. Leave it 0 only for a basic test; admin task approval and withdrawal controls require your ID.
4. Install Python 3.10 or newer.
5. Run `pip install -r requirements.txt`.
6. Run `python bot.py`.

## Admin commands
Add a task:
`/addtask Follow our channel | 20 | https://t.me/your_channel`

Users submit proof:
`/submit 1 https://example.com/proof`

Withdrawal request:
`/withdraw 100 bKash 01XXXXXXXXX`

Admin must manually verify and pay withdrawals outside Telegram, then press Mark paid. Rejected requests are refunded as points.

## Website images
`Pic1.svg` is the round profile image and `Pic2.svg` is the cover image used by `index.html`. Replace them with your own images, keeping the same filenames/extensions, or update the image paths in `index.html`.

## Important
This is a starter template, not a guaranteed-income service. Points have no cash value unless you fund and operate a genuine rewards program. Test privately first, protect the bot token, and keep backups of `first_bot.db`.
