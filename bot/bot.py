import os
import aiohttp
import discord

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CHARACTER_PROMPT = """
あなたはDiscord上のAIキャラクターです。
日本語で、短めに、自然な会話として返答してください。
攻撃的・過度な煽り・危険な助言は避けてください。
"""

intents = discord.Intents.default()
intents.messages = True

client = discord.Client(intents=intents)


async def ask_ollama(text: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": CHARACTER_PROMPT},
            {"role": "user", "content": text},
        ],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(OLLAMA_URL, json=payload, timeout=180) as res:
            res.raise_for_status()
            data = await res.json()
            return data["message"]["content"].strip()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if client.user not in message.mentions:
        return

    text = message.content
    text = text.replace(f"<@{client.user.id}>", "")
    text = text.replace(f"<@!{client.user.id}>", "")
    text = text.strip() or "呼ばれたので、軽く挨拶してください。"

    async with message.channel.typing():
        reply = await ask_ollama(text)

    await message.reply(
        reply[:1900],
        mention_author=False,
        allowed_mentions=discord.AllowedMentions.none(),
    )


client.run(DISCORD_TOKEN)