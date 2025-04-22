from flask import Flask, request, jsonify
from twilio.rest import Client
import os
import requests
from dotenv import load_dotenv
from processor import extract_parameters, transcribe_audio, summarize_config

load_dotenv()

# Twilio Config
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")  # WhatsApp sandbox number
TO_WHATSAPP = os.getenv("TO_WHATSAPP")  # User's verified number
RASPI_URL = os.getenv("RASPI_URL")  # e.g., http://<raspi-ip>:<port>/config

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

app = Flask(__name__)

# Simple in-memory storage for last parsed config
last_config = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    global last_config

    incoming = request.form
    msg_body = incoming.get("Body", "").strip().lower()
    media_type = incoming.get("MediaContentType0")
    media_url = incoming.get("MediaUrl0")

    if media_type and "audio" in media_type:
        print("🎤 Voice message received")
        msg_body = transcribe_audio(media_url)

    print("📩 Message Received:", msg_body)

    if msg_body in ["ok", "yes"]:
        # Send previously stored config to Raspberry Pi
        if last_config:
            try:
                res = requests.post(RASPI_URL, json=last_config)
                print("📡 Sent config to Raspberry Pi:", res.status_code)
                confirmation = "✅ Config sent to Raspberry Pi successfully."
            except Exception as e:
                print("❌ Could not reach Raspberry Pi:", str(e))
                confirmation = "❌ Failed to send config to Raspberry Pi."
        else:
            confirmation = "⚠️ No config to confirm. Please send a new instruction."

        client.messages.create(
            from_=TWILIO_FROM,
            to=TO_WHATSAPP,
            body=confirmation
        )

    else:
        # Regular instruction message
        params = extract_parameters(msg_body)
        summary = summarize_config(params, msg_body)

        last_config = params  # store for later confirmation

        client.messages.create(
            from_=TWILIO_FROM,
            to=TO_WHATSAPP,
            body=summary
        )

    return ("OK", 200)

@app.route("/")
def home():
    return "🌐 WhatsApp Smart Controller is LIVE ✅", 200

if __name__ == "__main__":
    app.run(debug=True)
