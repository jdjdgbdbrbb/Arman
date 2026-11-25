import threading
from bot import run_bot
from webapp import app
from db import init_db

def run_web():
    app.run(host="0.0.0.0", port= int(__import__("os").getenv("PORT", "8080")), threaded=True)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
