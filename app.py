import os
import threading
from flask import Flask, request, render_template
import requests
from list_parser import extract_list_from_file

app = Flask(__name__)

# --- GLOBAL DATA ---
bot_brain = {}       # { token: { keyword: reply } }
user_logs = {}       # optional
user_scores = {}     # { token: { chat_id: score } }

# --- WEBHOOK SETUP ---
def set_webhook(token, request_url):
    base_url = request_url.replace('/upload', '')
    webhook_url = f"{base_url}/webhook/{token}"
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
    try:
        requests.get(api_url, timeout=10)
    except:
        pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    bot_token = request.form.get('bot_token').strip()
    user_name = request.form.get('user_name').strip()
    user_dob = request.form.get('user_dob').strip()
    uploaded_file = request.files.get('file')

    if not bot_token or not uploaded_file:
        return "<h3>⚠️ Token aur File dono chahiye!</h3>", 400

    try:
        lines = extract_list_from_file(uploaded_file)
        if not lines:
            return "<h3>⚠️ File empty hai!</h3>", 400

        bot_brain[bot_token] = {}
        for line in lines:
            if ":" in line:
                parts = line.split(":", 1)
                bot_brain[bot_token][parts[0].strip().lower()] = parts[1].strip()
            else:
                bot_brain[bot_token][line.strip().lower()] = f"✅ Protocol {line.strip()} is Active!"

        user_logs[bot_token] = {"name": user_name, "dob": user_dob}
        user_scores[bot_token] = {}   # naya score dict
        set_webhook(bot_token, request.url)

        return f"""
        <div style="background:#0d1117; color:#58a6ff; padding:50px; text-align:center; font-family:monospace;">
            <h2 style="color:#238636;">⚙️ BOT BRAIN + SCORE SYSTEM READY</h2>
            <p><b>📦 Total Commands:</b> {len(bot_brain[bot_token])}</p>
            <p>🔢 Score system active: /score se points check karo</p>
            <a href="/" style="color:#238636;">← BACK TO PANEL</a>
        </div>
        """
    except Exception as e:
        return f"<h3>💥 Error: {str(e)}</h3>", 500

@app.route('/webhook/<token>', methods=['POST'])
def bot_webhook_handler(token):
    payload = request.get_json()
    if "message" in payload and "text" in payload["message"]:
        msg_obj = payload["message"]
        chat_id = msg_obj["chat"]["id"]
        msg_id = msg_obj["message_id"]
        user_text = msg_obj["text"].strip().lower()

        # /start command
        if user_text == "/start":
            reply = "🤖 System Online.\nCommands:\n/score - check your points\nSend any keyword from uploaded file"
            send_tg_reply(token, chat_id, msg_id, reply)
            return 'OK', 200

        # Score check
        if user_text == "/score":
            score = user_scores.get(token, {}).get(chat_id, 0)
            reply = f"🏆 **Your Score:** {score} points"
            send_tg_reply(token, chat_id, msg_id, reply)
            return 'OK', 200

        # Keyword matching
        if token in bot_brain:
            if user_text in bot_brain[token]:
                # INCREASE SCORE by 1
                if token not in user_scores:
                    user_scores[token] = {}
                user_scores[token][chat_id] = user_scores[token].get(chat_id, 0) + 1
                new_score = user_scores[token][chat_id]

                data_reply = bot_brain[token][user_text]
                # Append score info in reply
                reply_with_score = f"{data_reply}\n\n🎯 +1 point! Total score: {new_score}"
                send_tg_reply(token, chat_id, msg_id, reply_with_score)
            else:
                # silent if no match – but you can uncomment if needed
                pass

    return 'OK', 200

def send_tg_reply(token, chat_id, msg_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_to_message_id": msg_id
    }
    requests.post(url, json=payload)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
