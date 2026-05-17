import os
import time
import threading
from flask import Flask, render_template, request
import requests

# Parser logic import
from list_parser import extract_list_from_file

app = Flask(__name__)

# --- GLOBAL DATABASE ---
hosted_database = {}
user_logs = {}

# --- BACKGROUND CLEANER ---
def bg_expiry_cleaner():
    while True:
        current_time = time.time()
        for token in list(hosted_database.keys()):
            hosted_database[token] = [
                item for item in hosted_database[token] if current_time < item['expiry']
            ]
        time.sleep(30)

threading.Thread(target=bg_expiry_cleaner, daemon=True).start()

# --- WEBHOOK & MENU SETUP ---
def set_webhook(token, request_url):
    base_url = request_url.replace('/upload', '')
    webhook_url = f"{base_url}/webhook/{token}"
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
    try:
        r = requests.get(api_url, timeout=10)
        return r.json()
    except:
        return {"description": "Webhook Connection Failed"}

def setup_bot_menu(token):
    url = f"https://api.telegram.org/bot{token}/setMyCommands"
    payload = {
        "commands": [
            {"command": "start", "description": "🚀 Nexus System Start"},
            {"command": "list", "description": "📋 View Your File Data"},
            {"command": "owner", "description": "👑 View Commander Info"},
            {"command": "clear", "description": "🗑️ Clear Hosted Data"}
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
        return "<h3>⚠️ Details missing hain!</h3>", 400

    try:
        extracted_items = extract_list_from_file(uploaded_file)
        if not extracted_items:
            return "<h3>⚠️ File empty hai!</h3>", 400

        expiry_epoch = time.time() + (expiry_hours * 3600)
        hosted_database[bot_token] = [] # Reset old data for new file
        
        user_logs[bot_token] = {"name": user_name, "dob": user_dob}

        for item in extracted_items:
            hosted_database[bot_token].append({"data_content": item, "expiry": expiry_epoch})

        set_webhook(bot_token, request.url)
        setup_bot_menu(bot_token)

        return f"""
        <div style="background:#0d1117; color:#58a6ff; padding:50px; text-align:center; font-family:monospace; height:100vh;">
            <h2 style="color:#238636;">✅ DATA DEPLOYED & REPLY MODE ACTIVE</h2>
            <p><b>👑 Commander:</b> {user_name}</p>
            <p><b>📦 Extracted Items:</b> {len(extracted_items)}</p>
            <hr style="border:1px solid #30363d;">
            <p>Ab bot har command ka <b>Direct Reply</b> karega.</p>
            <br><a href="/" style="color:#238636;">[ BACK TO PANEL ]</a>
        </div>
        """
    except Exception as e:
        return f"<h3>💥 Error: {str(e)}</h3>", 500

# --- TELEGRAM WEBHOOK HANDLER (REPLY LOGIC) ---

@app.route('/webhook/<token>', methods=['POST'])
def bot_webhook_handler(token):
    payload = request.get_json()
    
    if "message" in payload and "text" in payload["message"]:
        msg_obj = payload["message"]
        chat_id = msg_obj["chat"]["id"]
        msg_id = msg_obj["message_id"] # Reply ke liye message ID
        text = msg_obj["text"].lower()

        # START COMMAND
        if text == "/start":
            msg = "🛰️ **Nexus Core Online**\n\nMain aapki file ke data ke hisab se reply karunga."
            send_tg_reply(token, chat_id, msg_id, msg)

        # OWNER COMMAND
        elif text == "/owner":
            info = user_logs.get(token, {"name": "Not Found", "dob": "N/A"})
            msg = f"👑 **HOST COMMANDER:**\n\n📛 Name: `{info['name']}`\n📅 DOB: `{info['dob']}`"
            send_tg_reply(token, chat_id, msg_id, msg)

        # LIST COMMAND (File Data Analysis)
        elif text == "/list":
            if token in hosted_database and hosted_database[token]:
                reply = "📋 **YOUR FILE DATA LIST:**\n\n"
                for idx, item in enumerate(hosted_database[token], 1):
                    rem_min = int((item['expiry'] - time.time()) / 60)
                    if rem_min > 0:
                        reply += f"🔹 {idx}. `{item['data_content']}` (⏳ {rem_min}m)\n"
            else:
                reply = "📭 **Database empty!** Pehle file upload karein."
            send_tg_reply(token, chat_id, msg_id, reply)

        # CLEAR COMMAND
        elif text == "/clear":
            hosted_database[token] = []
            send_tg_reply(token, chat_id, msg_id, "🗑️ Sabhi records delete kar diye gaye hain.")

    return 'OK', 200

# --- REPLY SENDING FUNCTION ---
def send_tg_reply(token, chat_id, msg_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_to_message_id": msg_id # Yeh line reply function on karti hai
    }
    requests.post(url, json=payload)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
