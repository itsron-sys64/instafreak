import discord
import re
import os
import asyncio
import tempfile
import glob
from dotenv import load_dotenv
import webserver
load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")

INSTA_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|p|tv)/([A-Za-z0-9_-]+)/?[^\s]*"
)

TIKTOK_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.|vt\.|m\.)?tiktok\.com/[^\s]+"
)


def rewrite_instagram(url: str) -> str:
    clean = url.split("?")[0]
    return re.sub(r"(?:www\.)?instagram\.com", "kkinstagram.com", clean, count=1)


async def download_tiktok(url: str, tmpdir: str) -> str | None:
    loop = asyncio.get_event_loop()

    def _download():
        try:
            import yt_dlp
            out_template = os.path.join(tmpdir, "tiktok.%(ext)s")
            ydl_opts = {
                "outtmpl": out_template,
                "format": "mp4/best",
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "socket_timeout": 30,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            videos = glob.glob(os.path.join(tmpdir, "tiktok.*"))
            videos = [v for v in videos if v.endswith((".mp4", ".mov", ".webm"))]
            return videos[0] if videos else None
        except Exception as e:
            print(f"[tiktok yt-dlp error] {e}")
            return None

    return await loop.run_in_executor(None, _download)


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    insta_matches = list(INSTA_PATTERN.finditer(message.content))
    tiktok_matches = list(TIKTOK_PATTERN.finditer(message.content))

    if not insta_matches and not tiktok_matches:
        return

    # Suppress Discord's broken default embeds
    try:
        await message.edit(suppress=True)
    except discord.Forbidden:
        pass

    # Instagram: URL-rewrite via kkinstagram.com so Discord embeds inline natively.
    # If Discord fails to fetch an embed within 3s, edit the reply to show an error.
    for match in insta_matches:
        rewritten = rewrite_instagram(match.group(0))
        sent = await message.reply(rewritten, mention_author=False)
        await asyncio.sleep(3)
        try:
            refreshed = await message.channel.fetch_message(sent.id)
            if not refreshed.embeds:
                await sent.edit(
                    content="❌ Could not embed that post. It may be private, age-restricted, or removed."
                )
        except Exception as e:
            print(f"[ig embed verify error] {e}")

    if not tiktok_matches:
        return

    async with message.channel.typing():
        for match in tiktok_matches:
            tiktok_url = match.group(0)
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = await download_tiktok(tiktok_url, tmpdir)

                if not file_path:
                    await message.reply(
                        "Could not download that TikTok. It may be private or region-locked.",
                        mention_author=False,
                    )
                    continue

                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb > 25:
                    await message.reply(
                        f"TikTok is too large to upload ({size_mb:.1f} MB, Discord limit is 25 MB).",
                        mention_author=False,
                    )
                    continue

                await message.reply(
                    file=discord.File(file_path, filename="tiktok.mp4"),
                    mention_author=False,
                )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable.")
    webserver.keep_alive()
    client.run(TOKEN)
