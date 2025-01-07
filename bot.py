import os
import json
import requests
import logging
from datetime import datetime
from telegram import Update, Chat
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ----------------------------
# 1. Чтение character.json
# ----------------------------
JSON_FILE = "character.json"
try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        character_data = json.load(f)
except FileNotFoundError:
    character_data = {}
    logging.warning(f"Файл {JSON_FILE} не найден! Используем пустые данные.")

# Извлекаем поля (если нет поля, используем пустой список/словарь/строку)
bot_name = character_data.get("name", "NoRugToken")
clients = character_data.get("clients", [])
model_provider = character_data.get("modelProvider", "openai")
bio_list = character_data.get("bio", [])
lore_list = character_data.get("lore", [])
knowledge = character_data.get("knowledge", [])
topics = character_data.get("topics", [])
style_info = character_data.get("style", {})
adjectives = character_data.get("adjectives", [])
mentions = character_data.get("mentions", [])

# Превращаем списки в строки для удобства
bio_str = "\n".join(bio_list)
lore_str = "\n".join(lore_list)
knowledge_str = "\n".join(knowledge) if isinstance(knowledge, list) else str(knowledge)
topics_str = "\n".join(topics)
adjectives_str = ", ".join(adjectives)

# Style может иметь разные секции (all, chat, post)
style_all_list = style_info.get("all", [])
style_chat_list = style_info.get("chat", [])
# Превращаем их в строки
style_all_str = "\n".join(style_all_list)
style_chat_str = "\n".join(style_chat_list)

# ----------------------------
# 2. Ключи и токены
# ----------------------------
# В реальном проекте лучше хранить их в переменных окружения, а не в коде
OPENROUTER_API_KEY = os.getenv("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", "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")
BOT_TOKEN = os.getenv("7695493113:AAFgHL-TTAEGAEmRa_qwzA_P4WZ_2oD8qiU", "7695493113:AAFgHL-TTAEGAEmRa_qwzA_P4WZ_2oD8qiU")

# OpenRouter endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ----------------------------
# 3. Формируем общий System Prompt
# ----------------------------
# Здесь мы объединим все поля (bio, lore, style, topics, etc.) в один большой контекст.
SYSTEM_PROMPT = f"""
You are {bot_name}, a crypto project focusing on security and transparency.

=== BIO ===
{bio_str}

=== LORE ===
{lore_str}

=== TOPICS ===
{topics_str}

=== KNOWLEDGE ===
{knowledge_str}

=== STYLE (ALL) ===
{style_all_str}

=== STYLE (CHAT) ===
{style_chat_str}

=== ADJECTIVES ===
{adjectives_str}

Rules:
1. Provide factual answers based on the info above.
2. If asked about yourself, only mention the details from LORE.
3. Follow the style guidelines: speak in a clear, transparent tone and greet users warmly.
4. Answer in a friendly and concise manner, unless the user asks for more detail.
"""

KEYWORDS = mentions

# ----------------------------
# 4. /start Команда
# ----------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = "Hello, I'm NoRugToken Bot! Ask me anything."
    # Если в character.json есть какое-то приветствие
    custom_greeting = character_data.get("greeting", "")
    if custom_greeting:
        greeting = custom_greeting

    await update.message.reply_text(greeting)

# ----------------------------
# 5. Обработчик сообщений
# ----------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user_text = message.text
    user_name = update.effective_user.full_name if update.effective_user else "Unknown User"
    user_id = update.effective_user.id if update.effective_user else "Unknown ID"

    # Получаем имя пользователя бота
    bot_username = (await context.bot.get_me()).username
    if not bot_username:
        logging.error("Не удалось получить имя пользователя бота.")
        return

    # Проверяем, упомянут ли бот в сообщении (без учёта регистра)
    if not any(f"@{bot_username.lower()}" in user_text.lower() for bot_username in [bot_username]):
        # Если хотите, чтобы бот отвечал на все сообщения, раскомментируйте следующую строку
        # pass
        # Иначе игнорируем сообщение
        return

    # Формируем запрос к OpenRouter
    payload = {
        "model": "openai/gpt-3.5-turbo",  # Или другую, если у вас есть доступ
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 500,
        "temperature": 0.3  # немного креативности
    }
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

    # Отправляем ответ
    await update.message.reply_text(gpt_answer)

    # Логирование в файл (при желании)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = (
        f"[{timestamp}]\n"
        f"User: {user_name} (ID: {user_id})\n"
        f"Message: {user_text}\n"
        f"Bot Reply: {gpt_answer}\n"
        f"------------------------\n"
    )
    with open("log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_line)

# ----------------------------
# 6. Запуск бота
# ----------------------------
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()

if __name__ == "__main__":
    main()
