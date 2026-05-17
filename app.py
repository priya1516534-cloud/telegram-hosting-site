import os, time, threading, requests
from flask import Flask, render_template, request
from list_parser import extract_list_from_file

app = Flask(__name__)

# Databases
bot_brain = {} 
user_logs = {}

def get_bot_info(token):
    """Token se bot ka asali naam aur username dhundne ke liye"""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        res = requests.get(url).json()
        if res['ok']:
            return res['result']['first_name'], res['result']['username']
    except:
        pass
    return "Unknown Bot", "N/A"

def set_webhook(token, req_url):
    base_url = req_url.replace('/upload', '')
    webhook_url = f"{base_url}/webhook/{token}"
    requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    token = request.form.get('bot_token').strip()
    name = request.form.get('user_name').strip()
    dob = request.form.get('user_dob').strip()
    file = request.files.get('file')

    if not token or not file:
        return "Missing Token/File", 400

    # Auto-fetch Bot Info
    b_name, b_username = get_bot_info(token)
    
    # Parse File
    lines = extract_list_from_file(file)
    bot_brain[token] = {}
    for line in lines:
        if ":" in line:
            k, v = line.split(":", 1)
            bot_brain[token][k.strip().lower()] = v.strip()
        else:
            bot_brain[token][line.strip().lower()] = f"✅ Protocol {line} Active!"

    user_logs[token] = {"name": name, "dob": dob}
    set_webhook(token, request.url)

    # Naya Dashboard page load karna details ke saath
    return render_template('dashboard.html', 
                           bot_name=b_name, 
                           bot_username=b_username, 
                           commander=name, 
                           cmd_count=len(bot_brain[token]))

@app.route('/webhook/<token>', methods=['POST'])
def bot_handler(token):
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        msg_id = msg["message_id"]
        txt = msg["text"].lower()

        if txt == "/start":
            reply = "🛰️ **Nexus Server Online**\nMain aapki file ke data par response dunga."
        elif token in bot_brain and txt in bot_brain[token]:
            reply = bot_brain[token][txt]
        else:
            return 'OK', 200

        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": reply, "reply_to_message_id": msg_id, "parse_mode": "Markdown"})
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))

