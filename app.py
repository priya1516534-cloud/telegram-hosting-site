import os, time, threading, requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

# --- IN-MEMORY DATABASE ---
bot_brain = {} 
user_logs = {}

# --- HTML STYLES (Isse Internal Server Error nahi aayega) ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>🛸 NEXUS DEPLOYER</title>
    <style>
        body { background: #0a0a0a; color: #00ff41; font-family: 'Courier New', monospace; text-align: center; }
        .box { max-width: 500px; margin: 50px auto; border: 2px solid #00ff41; padding: 30px; box-shadow: 0 0 20px #00ff41; border-radius: 10px; }
        input, button { width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #00ff41; color: #00ff41; font-weight: bold; }
        button { background: #00ff41; color: #000; cursor: pointer; transition: 0.3s; }
        button:hover { background: #000; color: #00ff41; }
    </style>
</head>
<body>
    <div class="box">
        <h2>⚔️ NEXUS CORE v3 ⚔️</h2>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="text" name="bot_token" placeholder="🔑 Bot Token" required>
            <input type="text" name="user_name" placeholder="👤 Commander Name" required>
            <input type="file" name="file" required>
            <button type="submit">🚀 INITIALIZE HOSTING</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>🛰️ DASHBOARD</title>
    <style>
        body { background: #000; color: #58a6ff; font-family: sans-serif; text-align: center; padding: 50px; }
        .card { max-width: 600px; margin: auto; background: #161b22; padding: 30px; border-radius: 15px; border: 1px solid #238636; }
        .bot-info { background: #0d1117; padding: 15px; border-left: 5px solid #238636; text-align: left; margin: 20px 0; font-family: monospace; }
        .green { color: #238636; }
    </style>
</head>
<body>
    <div class="card">
        <h2 class="green">✅ SYSTEM ONLINE</h2>
        <div class="bot-info">
            <p>🤖 <b>Bot:</b> {{ b_name }} (@{{ b_user }})</p>
            <p>👑 <b>Commander:</b> {{ commander }}</p>
            <p>📦 <b>Data Packets:</b> {{ count }}</p>
        </div>
        <p>Check your bot on Telegram now!</p>
        <a href="/" style="color: #238636; text-decoration: none;">[ Deploy Another ]</a>
    </div>
</body>
</html>
"""

# --- LOGIC FUNCTIONS ---
def get_bot_info(token):
    try:
        res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
        if res['ok']:
            return res['result']['first_name'], res['result']['username']
    except: pass
    return "Unknown Bot", "N/A"

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/upload', methods=['POST'])
def handle_upload():
    token = request.form.get('bot_token').strip()
    name = request.form.get('user_name').strip()
    file = request.files.get('file')

    if not token or not file: return "Error: Missing Data", 400

    # Auto-Webhook Setup
    webhook_url = f"{request.url_root}webhook/{token}"
    requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}")

    # Parsing Data
    try:
        content = file.read().decode('utf-8', errors='ignore')
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        bot_brain[token] = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                bot_brain[token][k.strip().lower()] = v.strip()
            else:
                bot_brain[token][line.strip().lower()] = f"✅ Protocol {line} Active!"
        
        b_name, b_user = get_bot_info(token)
        return render_template_string(DASHBOARD_HTML, b_name=b_name, b_user=b_user, commander=name, count=len(lines))
    except Exception as e:
        return f"File Error: {str(e)}", 500

@app.route('/webhook/<token>', methods=['POST'])
def bot_handler(token):
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id, msg_id, txt = msg["chat"]["id"], msg["message_id"], msg["text"].lower()

        reply = ""
        if txt == "/start":
            reply = "🛰️ **Nexus Server Online**\nMain aapki file ke data par reply karunga."
        elif token in bot_brain and txt in bot_brain[token]:
            reply = bot_brain[token][txt]
        
        if reply:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                          json={"chat_id": chat_id, "text": reply, "reply_to_message_id": msg_id, "parse_mode": "Markdown"})
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))
