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

JSON_FILE = "character.json"
try:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        character_data = json.load(f)
except FileNotFoundError:
    character_data = {}
    logging.warning(f"Файл {JSON_FILE} відсутній!")

bot_name = character_data.get("name", [])
links_list = character_data.get("links", [])
task_list = character_data.get("task", [])
bio_list = character_data.get("bio", [])
lore_list = character_data.get("lore", [])
knowledge = character_data.get("knowledge", [])
topics = character_data.get("topics", [])
style_info = character_data.get("style", {})
adjectives = character_data.get("adjectives", [])

introduction = character_data.get("introduction", [])

task_str = "\n".join(task_list)
bio_str = "\n".join(bio_list)
links_str = "\n".join(links_list)
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
You are {bot_name}.

=== TASK ===
{task_str}

=== LINKS === SEND ONLY LINK ITSELF!, NO () OR [] EXAMPLE: *тут додай щось від себе* Ось посилання: ... === LINKS ===

{links_str}

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

print(SYSTEM_PROMPT)

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

    if chat_type == Chat.PRIVATE:
        should_respond = True
    else:
        should_respond = f"@{bot_username.lower()}" in user_text.lower()

    if not should_respond:
        return

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 500,  #  К-кість токенів
        "temperature": 0.3  # Креативність
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

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(introduction)

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CommandHandler('start', start_handler))
    application.run_polling()

if __name__ == "__main__":
    main()