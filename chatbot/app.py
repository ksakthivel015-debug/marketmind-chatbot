import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import (
    ERROR_MESSAGE,
    MAX_HISTORY,
    MAX_MESSAGE_LENGTH,
    MODEL_NAME,
    SYSTEM_PROMPT,
    TEMPERATURE,
)

load_dotenv()

app = Flask(__name__)
API_KEY = os.getenv("GEMINI_API_KEY", "")
if not API_KEY or API_KEY.startswith("your_"):
    print("Warning: set a valid GEMINI_API_KEY in the .env file.")

client = genai.Client(api_key=API_KEY)


def describe_error(error):
    text = str(error).lower()
    if "api key" in text or "api_key" in text or "401" in text or "403" in text:
        return "Invalid or missing Gemini API key. Check GEMINI_API_KEY in your .env file."
    if "429" in text or "quota" in text or "exhausted" in text:
        return "Gemini API quota exceeded. Please wait a moment and try again."
    if "404" in text or "not found" in text:
        return "Model not found. Check MODEL_NAME in chatbot_config.py."
    return ERROR_MESSAGE


def build_contents(history, message):
    contents = []
    for item in history[-MAX_HISTORY:]:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        role = "user" if item.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    return contents


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history") or []

    if not message:
        return jsonify(error="Please type a message."), 400
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify(error=f"Message is too long (max {MAX_MESSAGE_LENGTH} characters)."), 400

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=build_contents(history, message),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=TEMPERATURE,
            ),
        )
        reply = (response.text or "").strip() or ERROR_MESSAGE
    except Exception as error:
        app.logger.exception("Gemini request failed")
        return jsonify(error=describe_error(error)), 500

    return jsonify(reply=reply)


if __name__ == "__main__":
    app.run(debug=True)
