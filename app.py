import os, time, threading, requests
from flask import Flask, request, render_template_string

app = Flask(__name__)

# --- DATABASE ---
bot_brain = {} 

# --- UI DESIGN (CSS + JS + HTML) ---
# Isme Loading Bar aur Image Animation sab hai
UI_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🛰️ NEXUS COMMANDER v4</title>
    <style>
        body { background: #000; color: #00ff41; font-family: 'Courier New', monospace; overflow: hidden; margin: 0; }
        
        /* 1. Splash Screen Styling */
        #splash { height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #000; }
        .nexus-img { width: 150px; height: 150px; border-radius: 50%; border: 2px solid #00ff41; box-shadow: 0 0 20px #00ff41; margin-bottom: 20px; animation: pulse 2s infinite; }
        
        /* Loading Bar Container */
        .progress-container { width: 80%; max-width: 400px; height: 10px; border: 1px solid #00ff41; position: relative; border-radius: 5px; overflow: hidden; }
        .progress-bar { width: 0%; height: 100%; background: #00ff41; box-shadow: 0 0 10px #00ff41; transition: width 0.1s; }
        .percent { margin-top: 10px; font-size: 18px; font-weight: bold; }

        /* 2. Main Content (Hidden initially) */
        #main-site { display: none; padding: 20px; }
        .box { max-width: 500px; margin: 20px auto; border: 2px solid #00ff41; padding: 30px; box-shadow: 0 0 15px #00ff41; border-radius: 10px; }
        input, button { width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #00ff41; color: #00ff41; font-weight: bold; }
        button { background: #00ff41; color: #000; cursor: pointer; }
        
        /* Green Blinking Light */
        .blinker { height: 12px; width: 12px; background-color: #00ff41; border-radius: 50%; display: inline-block; margin-right: 10px; animation: blink 1s infinite; box-shadow: 0 0 10px #00ff41; }

        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.1; } 100% { opacity: 1; } }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    </style>
</head>
<body>

    <div id="splash">
        <img src="https://i.pinimg.com/736x/0a/76/f5/0a76f5787f7a77e8a93e3e015d8f6d6c.jpg" class="nexus-img" alt="Nexus Logo">
        <div class="progress-container">
            <div id="progress" class="progress-bar"></div>
        </div>
        <div class="percent" id="percent">0%</div>
        <p style="letter-spacing: 3px;">INITIALIZING NEXUS ENGINE...</p>
    </div>

    <div id="main-site">
        <div class="box">
            <h2><span class="blinker"></span>NEXUS HOSTING CORE</h2>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <input type="text" name="bot_token" placeholder="🔑 Bot Token" required>
                <input type="text" name="user_name" placeholder="👤 Commander Name" required>
                <input type="file" name="file" required>
                <button type="submit">🔥 DEPLOY MODULE</button>
            </form>
        </div>
    </div>

    <script>
        // Loading Logic
        let i = 0;
        function move() {
            if (i == 0) {
                i = 1;
                let elem = document.getElementById("progress");
                let percentTxt = document.getElementById("percent");
                let width = 0;
                let id = setInterval(frame, 40); // Speed set yahan se hogi
                function frame() {
                    if (width >= 100) {
                        clearInterval(id);
                        document.getElementById("splash").style.display = "none";
                        document.getElementById("main-site").style.display = "block";
                        document.body.style.overflow = "auto";
                    } else {
                        width++;
                        elem.style.width = width + "%";
                        percentTxt.innerHTML = width + "%";
                    }
                }
            }
        }
        window.onload = move;
    </script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        body { background: #000; color: #58a6ff; font-family: sans-serif; text-align: center; padding: 50px; }
        .card { max-width: 600px; margin: auto; background: #161b22; padding: 30px; border-radius: 15px; border: 1px solid #238636; }
        .blinker { height: 15px; width: 15px; background: #238636; border-radius: 50%; display: inline-block; animation: blink 0.8s infinite; box-shadow: 0 0 15px #238636; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0; } 100% { opacity: 1; } }
        .bot-info { background: #0d1117; padding: 15px; border-left: 5px solid #238636; text-align: left; margin: 20px 0; font-family: monospace; }
    </style>
</head>
<body>
    <div class="card">
        <h2><span class="blinker"></span> LIVE HOSTING ACTIVE</h2>
        <div class="bot-info">
            <p>🤖 <b>Bot:</b> {{ b_name }} (@{{ b_user }})</p>
            <p>📦 <b>Commands Loaded:</b> {{ count }}</p>
        </div>
        <p>Bot is now monitoring your file data.</p>
        <a href="/" style="color:#238636; text-decoration:none;">[ Back to Console ]</a>
    </div>
</body>
</html>
"""

# --- BACKEND LOGIC ---
@app.route('/')
def index():
    return render_template_string(UI_LAYOUT)

@app.route('/upload', methods=['POST'])
def handle_upload():
    token = request.form.get('bot_token').strip()
    name = request.form.get('user_name').strip()
    file = request.files.get('file')

    if not token or not file: return "Error", 400

    # Auto Webhook
    webhook_url = f"{request.url_root}webhook/{token}"
    requests.get(f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}")

    try:
        content = file.read().decode('utf-8', errors='ignore')
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        bot_brain[token] = {}
        for line in lines:
            if ":" in line:
                k, v = line.split(":", 1)
                bot_brain[token][k.strip().lower()] = v.strip()
            else:
                bot_brain[token][line.strip().lower()] = f"✅ Data: {line}"
        
        # Get Bot Name
        res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
        b_name = res['result']['first_name'] if res['ok'] else "Bot"
        b_user = res['result']['username'] if res['ok'] else "N/A"

        return render_template_string(DASHBOARD_HTML, b_name=b_name, b_user=b_user, count=len(lines))
    except:
        return "Internal Error", 500

@app.route('/webhook/<token>', methods=['POST'])
def bot_handler(token):
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        msg = data["message"]
        chat_id, msg_id, txt = msg["chat"]["id"], msg["message_id"], msg["text"].lower()
        if token in bot_brain and txt in bot_brain[token]:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                          json={"chat_id": chat_id, "text": bot_brain[token][txt], "reply_to_message_id": msg_id})
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))
