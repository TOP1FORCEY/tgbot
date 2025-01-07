import os
import json
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# 1. Загрузка character.json
JSON_FILE = "character.json"
try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        character_data = json.load(f)
except FileNotFoundError:
    character_data = {}
    logging.warning(f"Файл {JSON_FILE} не найден! Использую пустые данные.")

# Извлекаем поля (bio, lore)
bot_bio_list = character_data.get("bio", [])
bot_lore_list = character_data.get("lore", [])
bot_bio = "\n".join(bot_bio_list) if isinstance(bot_bio_list, list) else str(bot_bio_list)
bot_lore = "\n".join(bot_lore_list) if isinstance(bot_lore_list, list) else str(bot_lore_list)

# 2. Считываем ключи из переменных окружения
OPENROUTER_API_KEY = ("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")
if not OPENROUTER_API_KEY:
    raise ValueError("Не установлен OPENROUTER_API_KEY в переменных окружения.")

BOT_TOKEN = ("7695493113:AAFgHL-TTAEGAEmRa_qwzA_P4WZ_2oD8qiU")
if not BOT_TOKEN:
    raise ValueError("Не установлен BOT_TOKEN в переменных окружения.")

# 3. URL OpenRouter
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 4. Формируем system prompt, включая данные из JSON
SYSTEM_PROMPT = f"""\
You are NoRugToken, a crypto project focusing on security and transparency.

== BIO ==
{bot_bio}

== LORE ==
{bot_lore}

Rules:
- Provide factual answers based on the info above.
- If asked about liquidity, mention the details from LORE (like "Total liquidity is 100m dollars...").
- Be concise and friendly.
"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если в JSON есть greeting, используем его
    greeting = character_data.get("greeting", "Hello, I'm NoRugToken Bot!")
    await update.message.reply_text(greeting)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # Формируем тело POST-запроса
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 200,
        "temperature": 0.1
    }

    # Заголовки
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://my-cool-project.com"
    }

    try:
        response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        gpt_answer = data["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"OpenRouter API error: {e}")
        gpt_answer = "Sorry, an error occurred while fetching data from OpenRouter."

    await update.message.reply_text(gpt_answer)

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()

if __name__ == "__main__":
    main()