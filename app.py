import os
import time
import threading
from flask import Flask, render_template, request
import requests

# Parser function import
from list_parser import extract_list_from_file

app = Flask(__name__)

# Main Storage Dictionary
hosted_database = {}
user_logs = {}  

def bg_expiry_cleaner():
    """Time khatam hone par elements ko auto-delete karne ke liye"""
    while True:
        current_time = time.time()
        for token in list(hosted_database.keys()):
            hosted_database[token] = [
                item for item in hosted_database[token] if current_time < item['expiry']
            ]
        time.sleep(30)

# Cleaner thread start
threading.Thread(target=bg_expiry_cleaner, daemon=True).start()

def setup_bot_menu(token):
    """Telegram interface ke andar dynamic command list set karna"""
    url = f"https://api.telegram.org/bot{token}/setMyCommands"
    payload = {
        "commands": [
            {"command": "start", "description": "🚀 Check Server Connection"},
            {"command": "list", "description": "📋 Show Active Extracted Items"},
            {"command": "owner", "description": "👑 Show Host Commander Details"},
            {"command": "clear", "description": "🗑️ Wipe Hosting Dashboard"}
        ]
    }
    try: requests.post(url, json=payload, timeout=5)
    except: pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    bot_token = request.form.get('bot_token').strip()
    user_name = request.form.get('user_name').strip()
    user_dob = request.form.get('user_dob').strip()
    expiry_hours = int(request.form.get('expiry', 1))
    uploaded_file = request.files.get('file')

    if not bot_token or not uploaded_file or not user_name or not user_dob:
        return "<h3>⚠️ Error: Sabhi boxes ko fill karein!</h3>", 400

    try:
        extracted_items = extract_list_from_file(uploaded_file)
        
        if not extracted_items:
            return "<h3>⚠️ Error: File khali hai ya parsing block ho gayi!</h3>", 400

        expiry_epoch = time.time() + (expiry_hours * 3600)

        if bot_token not in hosted_database:
            hosted_database[bot_token] = []
            setup_bot_menu(bot_token)
        
        user_logs[bot_token] = {
            "name": user_name,
            "dob": user_dob
        }

        for item in extracted_items:
            hosted_database[bot_token].append({
                "data_content": item,
                "expiry": expiry_epoch
            })

        return f"""
        <div style="background:#0d1117; color:#58a6ff; padding:50px; text-align:center; font-family:monospace; height:100vh;">
            <h2>🎉 HOSTING SYSTEM ENGAGED SUCCESSFULLY 🎉</h2>
            <p><b>👑 Host Commander:</b> {user_name} (📅 DOB: {user_dob})</p>
            <p><b>📦 Extracted Lines Count:</b> {len(extracted_items)} working packets loaded.</p>
            <p><b>⏳ Lifespan Protocol:</b> {expiry_hours} Hour(s)</p>
            <p style="color:#8b949e;">🤖 Bot par jao aur type karo: <b>/list</b> (list check karne ke liye) aur <b>/owner</b> (credentials check karne ke liye).</p>
            <br><a href="/" style="color:#238636; text-decoration:none;">✨ [ BACK TO CONTROL DASHBOARD ] ✨</a>
        </div>
        """
    except Exception as e:
        return f"<h3>💥 Core Server Crash: {str(e)}</h3>", 500

@app.route('/webhook/<token>', methods=['POST'])
def bot_webhook_handler(token):
    payload = request.get_json()
    if "message" in payload and "text" in payload["message"]:
        chat_id = payload["message"]["chat"]["id"]
        command = payload["message"]["text"].lower()

        if command == "/start":
            send_tg_msg(token, chat_id, "🛰️ **Nexus Server Core Online** 🛰️\n\n🔹 Use `/list` to view elements.\n🔹 Use `/owner` to view session log data.")
        
        elif command == "/owner":
            if token in user_logs:
                info = user_logs[token]
                reply = f"👑 **HOST COMMANDER PROFILE LOGS:**\n\n📛 **Name:** `{info['name']}`\n📅 **Date of Birth:** `{info['dob']}`\n⚙️ **Status:** Active Account"
            else:
                reply = "📭 **No session log records found for this token.**"
            send_tg_msg(token, chat_id, reply)

        elif command == "/list":
            if token in hosted_database and hosted_database[token]:
                reply = "📋 **ACTIVE HOSTED ITEMS LIST DATA:**\n\n"
                for idx, item in enumerate(hosted_database[token], 1):
                    rem_min = int((item['expiry'] - time.time()) / 60)
                    if rem_min > 0:
                        reply += f"💎 **Item {idx}:** `{item['data_content']}`\n⏳ Expiring in: `{rem_min} minutes`\n\n"
            else:
                reply = "📭 **Hosted list database is currently empty!** Website par jaakar naya data inject karein."
            send_tg_msg(token, chat_id, reply)

        elif command == "/clear":
            if token in hosted_database: hosted_database[token] = []
            if token in user_logs: del user_logs[token]
            send_tg_msg(token, chat_id, "🗑️ **All dynamic session database maps cleared successfully.**")

    return 'OK', 200

def send_tg_msg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
  
