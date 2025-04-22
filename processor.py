# processor.py

import openai
import requests
import os
import base64
import json
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def load_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    else:
        return {
            "feeding_hours": "7-11-3-7",
            "advance_notice_minutes": 30
        }

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f)

def transcribe_audio(audio_url):
    print("🎙 Downloading voice file from:", audio_url)
    audio_data = requests.get(audio_url).content

    with open("temp_voice.ogg", "wb") as f:
        f.write(audio_data)

    with open("temp_voice.ogg", "rb") as f:
        transcription = openai.audio.transcriptions.create(
            file=f,
            model="whisper-1"
        )
    print("📝 Transcription:", transcription.text)
    return transcription.text

def extract_parameters(text_input):
    config = load_config()
    current_feeding = config.get("feeding_hours", "7-11-3-7")
    default_notice = config.get("advance_notice_minutes", 30)

    prompt = f'''
You're an intelligent assistant that reads messages from shrimp farmers sent via WhatsApp.

The farmer will send a **casual sentence** in Telugu, English, or Hinglish asking to either:
- Start the process (example: "start capturing every 4 hours for 10 seconds")
- Stop the process
- Change the timer or duration

📍 They might also mention a **reference** time:
- "now" (start from now)
- "7am" (start at 7am)
- "before_feeding" (trigger before each feeding time)

🐟 Feeding Times:
- By default assume feeding times are **{current_feeding}**
- But if farmer mentions custom feeding hours (e.g., "6-10-2-6"), extract that as a string

⏰ Advance Notice:
- Default is {default_notice} minutes before feeding
- If user specifies a different lead time (e.g., "10 mins before feeding"), extract it as "advance_notice_minutes"

👉 Your job is to return a valid JSON object with these fields:
- "status": "start" or "stop"
- "timer_interval_hours": integer
- "video_duration_seconds": integer
- "timer_reference": "now", "7am", or "before_feeding"
- "feeding_hours": string (like "7-11-3-7")
- "advance_notice_minutes": integer (default 30)

🎯 Output JSON only. No markdown. No explanation.

Input:
"""{text_input}"""
'''

    result = {}

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        extracted = response.choices[0].message.content.strip()

        if extracted.startswith("```json"):
            extracted = extracted.replace("```json", "").replace("```", "").strip()

        result = json.loads(extracted)

    except Exception as e:
        print("❌ Error parsing GPT output:", e)

    # Update stored config if feeding_hours or advance_notice_minutes have changed
    if result.get("feeding_hours") and result["feeding_hours"] != current_feeding:
        config["feeding_hours"] = result["feeding_hours"]
    if result.get("advance_notice_minutes") and result["advance_notice_minutes"] != default_notice:
        config["advance_notice_minutes"] = result["advance_notice_minutes"]

    save_config(config)

    print("🧠 Extracted Params:", result)
    return result

def summarize_config(params, original_text):
    summary = []

    if "timer_interval_hours" in params:
        summary.append(f"⏱ Interval: every {params['timer_interval_hours']} hour(s)")

    if "video_duration_seconds" in params:
        summary.append(f"🎥 Duration: {params['video_duration_seconds']} seconds")

    if "status" in params:
        status = "▶️ Start" if params["status"] == "start" else "🛑 Stop"
        summary.append(f"🧩 Capture Status: {status}")

    if params.get("timer_reference") == "before_feeding":
        if "feeding_hours" in params:
            summary.append(f"🍤 Feeding Times: {params['feeding_hours']}")
        if "advance_notice_minutes" in params:
            summary.append(f"⏳ Alert {params['advance_notice_minutes']} min before feeding")

    return (
        f"🧾 Original Message:\n{original_text}\n\n"
        f"✅ Detected Config:\n" + "\n".join(summary) + "\n\n"
        f"👉 Reply 'OK' to confirm or 'Edit' to send changes."
    )
