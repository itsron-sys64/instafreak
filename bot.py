import discord
import re
import os
import asyncio
from dotenv import load_dotenv
import webserver
load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")

INSTA_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|reels|p)/[^\s]+",
    re.IGNORECASE,
)

TIKTOK_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/[^\s]+"
)


def rewrite_instagram(url: str) -> str:
    return re.sub(r"(?:www\.)?instagram\.com", "kkinstagram.com", url, count=1)


def rewrite_tiktok(url: str) -> str:
    clean = url.split("?")[0]
    return re.sub(r"(?:[a-z0-9-]+\.)?tiktok\.com", "tnktok.com", clean, count=1)


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def post_with_embed_check(message: discord.Message, rewritten_url: str, error_text: str):
    """Reply with the rewritten URL, then edit it to an error if Discord doesn't embed."""
    sent = await message.reply(rewritten_url, mention_author=False)
    await asyncio.sleep(5)
    try:
        refreshed = await message.channel.fetch_message(sent.id)
        if not refreshed.embeds:
            await sent.edit(content=error_text)
    except Exception as e:
        print(f"[embed verify error] {e}")


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    insta_matches = INSTA_PATTERN.findall(message.content)
    tiktok_matches = list(TIKTOK_PATTERN.finditer(message.content))

    if not insta_matches and not tiktok_matches:
        return

    # Suppress Discord's broken default embeds
    try:
        await message.edit(suppress=True)
    except discord.Forbidden:
        pass

    for match in insta_matches:
        rewritten = rewrite_instagram(match)
        await post_with_embed_check(
            message,
            rewritten,
            "❄️ Could not embed that post. It may be private, age-restricted, or removed.",
        )

    for match in tiktok_matches:
        rewritten = rewrite_tiktok(match.group(0))
        await post_with_embed_check(
            message,
            rewritten,
            "❄️ Could not embed that TikTok. It may be private, removed, or region-locked.",
        )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable.")
    webserver.keep_alive()
    client.run(TOKEN)
