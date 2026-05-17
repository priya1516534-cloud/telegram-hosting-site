import os
import time
import threading
from flask import Flask, render_template, request, jsonify
import requests

# Parser logic import
from list_parser import extract_list_from_file

app = Flask(__name__)

# --- GLOBAL DATABASE ---
hosted_database = {}
user_logs = {}

# --- BACKGROUND CLEANER ---
def bg_expiry_cleaner():
    """Time khatam hone par elements ko auto-delete karne wala system"""
    while True:
        current_time = time.time()
        for token in list(hosted_database.keys()):
            hosted_database[token] = [
                item for item in hosted_database[token] if current_time < item['expiry']
            ]
        time.sleep(30)

# Cleaner thread chalu karein
threading.Thread(target=bg_expiry_cleaner, daemon=True).start()

# --- WEBHOOK HELPER ---
def set_webhook(token, request_url):
    """Bot ko Telegram server se connect karne ka auto-system"""
    # Request URL se base domain nikalna (e.g., https://app.onrender.com)
    base_url = request_url.replace('/upload', '')
    webhook_url = f"{base_url}/webhook/{token}"
    
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
    try:
        r = requests.get(api_url, timeout=10)
        return r.json()
    except Exception as e:
        return str(e)

def setup_bot_menu(token):
    """Bot ke andar buttons/commands set karna"""
    url = f"https://api.telegram.org/bot{token}/setMyCommands"
    payload = {
        "commands": [
            {"command": "start", "description": "🚀 Nexus System Start"},
            {"command": "list", "description": "📋 View Hosted List"},
            {"command": "owner", "description": "👑 View Host Commander"},
            {"command": "clear", "description": "🗑️ Clear My Database"}
        ]
    }
    requests.post(url, json=payload)

# --- WEB ROUTES ---

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

    if not bot_token or not uploaded_file or not user_name:
        return "<h3>⚠️ Error: Details incomplete hain!</h3>", 400

    try:
        # 1. File se data nikalna
        extracted_items = extract_list_from_file(uploaded_file)
        if not extracted_items:
            return "<h3>⚠️ Error: File ke andar koi data nahi mila!</h3>", 400

        # 2. Database mein save karna
        expiry_epoch = time.time() + (expiry_hours * 3600)
        if bot_token not in hosted_database:
            hosted_database[bot_token] = []
        
        user_logs[bot_token] = {"name": user_name, "dob": user_dob}

        for item in extracted_items:
            hosted_database[bot_token].append({"data_content": item, "expiry": expiry_epoch})

        # 3. AUTO WEBHOOK ACTIVATION (Sabse Important)
        wh_status = set_webhook(bot_token, request.url)
        setup_bot_menu(bot_token)

        return f"""
        <div style="background:#0d1117; color:#58a6ff; padding:50px; text-align:center; font-family:monospace; height:100vh;">
            <h2 style="color:#238636;">✅ SYSTEM DEPLOYED SUCCESSFULLY</h2>
            <p><b>👑 Commander:</b> {user_name}</p>
            <p><b>📦 Data Packets:</b> {len(extracted_items)} items extracted.</p>
            <p><b>📡 Webhook Status:</b> {wh_status.get('description', 'Connected')}</p>
            <hr style="border:1px solid #30363d;">
            <p style="color:#8b949e;">Bot ab online hai! Telegram par <b>/start</b> check karein.</p>
            <br><a href="/" style="color:#238636; text-decoration:none;">[ BACK TO PANEL ]</a>
        </div>
        """
    except Exception as e:
        return f"<h3>💥 Crash Error: {str(e)}</h3>", 500

# --- TELEGRAM WEBHOOK HANDLER ---

@app.route('/webhook/<token>', methods=['POST'])
def bot_webhook_handler(token):
    payload = request.get_json()
    
    if "message" in payload and "text" in payload["message"]:
        chat_id = payload["message"]["chat"]["id"]
        text = payload["message"]["text"].lower()

        # START COMMAND
        if text == "/start":
            msg = "🛰️ **Nexus Core Online**\n\nSystem aapki file ke data ko host kar raha hai.\n\nCommands:\n/list - 📋 Data dekhne ke liye\n/owner - 👑 Commander info"
            send_tg_msg(token, chat_id, msg)

        # OWNER COMMAND
        elif text == "/owner":
            info = user_logs.get(token, {"name": "Unknown", "dob": "N/A"})
            msg = f"👑 **HOST COMMANDER:**\n\n📛 Name: `{info['name']}`\n📅 DOB: `{info['dob']}`"
            send_tg_msg(token, chat_id, msg)

        # LIST COMMAND
        elif text == "/list":
            if token in hosted_database and hosted_database[token]:
                reply = "📋 **ACTIVE DATA PACKETS:**\n\n"
                for idx, item in enumerate(hosted_database[token], 1):
                    rem_min = int((item['expiry'] - time.time()) / 60)
                    if rem_min > 0:
                        reply += f"{idx}. `{item['data_content']}` (⏳ {rem_min}m)\n"
            else:
                reply = "📭 **List empty hai!** Pehle website se host karein."
            send_tg_msg(token, chat_id, reply)

        # CLEAR COMMAND
        elif text == "/clear":
            hosted_database[token] = []
            send_tg_msg(token, chat_id, "🗑️ Sabhi data records wipe kar diye gaye hain.")

    return 'OK', 200

def send_tg_msg(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
