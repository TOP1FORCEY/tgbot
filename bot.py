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

JSON_FILE = "character.json"
try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        character_data = json.load(f)
except FileNotFoundError:
    character_data = {}
    logging.warning(f"Файл {JSON_FILE} не найден! Используем пустые данные.")

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

bio_str = "\n".join(bio_list)
lore_str = "\n".join(lore_list)
knowledge_str = "\n".join(knowledge) if isinstance(knowledge, list) else str(knowledge)
topics_str = "\n".join(topics)
adjectives_str = ", ".join(adjectives)

style_all_list = style_info.get("all", [])
style_chat_list = style_info.get("chat", [])
style_all_str = "\n".join(style_all_list)
style_chat_str = "\n".join(style_chat_list)

OPENROUTER_API_KEY = character_data.get("OPENROUTER_API_KEY", [])
BOT_TOKEN = character_data.get("BOT_TOKEN", [])

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


# ----------------------------System Prompt-----------------------------
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

# ----------------------------START----------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user_text = message.text
    user_name = update.effective_user.full_name if update.effective_user else "Unknown User"
    user_id = update.effective_user.id if update.effective_user else "Unknown ID"
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    bot_username = (await context.bot.get_me()).username

    if not bot_username:
        logging.error("Bot username error.")
        return

    # Respond logic: respond in private chats or if mentioned in group chats
    if chat_type == Chat.PRIVATE:
        should_respond = True
    else:
        # Respond only if bot is mentioned in group chats
        should_respond = f"@{bot_username.lower()}" in user_text.lower()

    if not should_respond:
        return

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 500,
        "temperature": 0.3  # Adjust creativity level
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

    await message.reply_text(gpt_answer)

    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    log_line = (
        
        f"\n\n{time}\n"
        f"In chat: {chat_id} (type: {chat_type})\n"
        f"User: {user_name} (ID: {user_id})\n"
        f"Message: {user_text}\n"
        f"Bot Reply: {gpt_answer}\n"
    )

    logging.info(str(log_line))

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.run_polling()
if __name__ == "__main__":
    main()