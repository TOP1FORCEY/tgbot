import discord
import json
import requests
import logging
import os
from datetime import datetime

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
    logging.warning(f"File {JSON_FILE} is missing!")

# Bot configuration
bot_name = character_data.get("name", "Bot")
introduction = character_data.get("introduction", "Hello! I am here to assist you.")
OPENROUTER_API_KEY = character_data.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
BOT_TOKEN = "MTMyNzI3NTQwNjIxNDAzNzUxNA.GQGXcG.ECx7yno2KqkZ" + "cLPUg5LIpuMcy_YgZ9dy5o-C1c"

if not OPENROUTER_API_KEY or not BOT_TOKEN:
    logging.error("Missing API key or bot token. Check character.json or environment variables.")
    exit(1)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# System prompt
SYSTEM_PROMPT = f"""
You are {bot_name}.

=== BIO ===
{character_data.get('bio', '')}

=== LORE ===
{character_data.get('lore', '')}

=== TOPICS ===
{character_data.get('topics', '')}

=== KNOWLEDGE ===
{character_data.get('knowledge', '')}

Rules:
1. Provide factual answers based on the info above.
2. If asked about yourself, only mention the details from LORE.
3. Follow the style guidelines: speak in a clear, transparent tone and greet users warmly.
4. Answer in a friendly and concise manner, unless the user asks for more detail.
"""

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logging.info(f"Bot {client.user} is now running.")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    user_text = message.content
    should_respond = False

    if isinstance(message.channel, discord.DMChannel):
        should_respond = True
    elif client.user.mentioned_in(message):
        should_respond = True
        user_text = user_text.replace(f"<@{client.user.id}>", "").strip()

    if not should_respond:
        return

    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "max_tokens": 500,
        "temperature": 0.3
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_API_KEY}"
    }

    try:
        response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        gpt_answer = data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        logging.error(f"OpenRouter API error: {e}")
        gpt_answer = "Sorry, an error occurred while fetching data from OpenRouter."
    except KeyError:
        logging.error("Unexpected response structure from OpenRouter API.")
        gpt_answer = "Sorry, I couldn't process the request properly."

    await message.channel.send(gpt_answer)


    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = (
        f"\n\n{time}\n"
        f"In channel: {message.channel} (type: {'DM' if isinstance(message.channel, discord.DMChannel) else 'Server'})\n"
        f"User: {message.author} (ID: {message.author.id})\n"
        f"Message: {user_text}\n"
        f"Bot Reply: {gpt_answer}\n"
    )
    logging.info(str(log_line))

try:
    client.run(BOT_TOKEN)
except discord.LoginFailure:
    logging.error("Invalid BOT_TOKEN. Please check your configuration.")
