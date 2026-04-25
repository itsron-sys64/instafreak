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

MEDIA_EXTS = (".mp4", ".mov", ".webm", ".jpg", ".jpeg", ".png", ".webp", ".gif")
DISCORD_FILE_LIMIT_MB = 25
DISCORD_MAX_ATTACHMENTS = 10


def _collect_media(tmpdir: str) -> list[str]:
    files = []
    for ext in MEDIA_EXTS:
        files.extend(glob.glob(os.path.join(tmpdir, f"**/*{ext}"), recursive=True))
    return sorted(files)


async def download_tiktok(url: str, tmpdir: str) -> list[str]:
    loop = asyncio.get_event_loop()

    def _download():
        try:
            import yt_dlp
            out_template = os.path.join(tmpdir, "tiktok_%(playlist_index)s.%(ext)s")
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
            return _collect_media(tmpdir)
        except Exception as e:
            print(f"[tiktok yt-dlp error] {e}")
            return []

    return await loop.run_in_executor(None, _download)


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def download_instagram(url: str, tmpdir: str) -> list[str]:
    loop = asyncio.get_event_loop()

    def _download():
        try:
            import yt_dlp
            out_template = os.path.join(tmpdir, "ig_%(playlist_index)s.%(ext)s")
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
            return _collect_media(tmpdir)
        except Exception as e:
            print(f"[instagram yt-dlp error] {e}")
            return []

    return await loop.run_in_executor(None, _download)


def _chunk_for_discord(files: list[str]) -> tuple[list[list[str]], list[str]]:
    """Split files into Discord-sendable batches and a list of skipped (too-large) files."""
    batches: list[list[str]] = []
    skipped: list[str] = []
    current: list[str] = []
    current_size_mb = 0.0
    limit_bytes = DISCORD_FILE_LIMIT_MB * 1024 * 1024

    for f in files:
        size_mb = os.path.getsize(f) / (1024 * 1024)
        if os.path.getsize(f) > limit_bytes:
            skipped.append(f)
            continue
        if len(current) >= DISCORD_MAX_ATTACHMENTS or current_size_mb + size_mb > DISCORD_FILE_LIMIT_MB:
            batches.append(current)
            current = []
            current_size_mb = 0.0
        current.append(f)
        current_size_mb += size_mb

    if current:
        batches.append(current)
    return batches, skipped


async def send_media(message: discord.Message, files: list[str]) -> None:
    batches, skipped = _chunk_for_discord(files)
    for batch in batches:
        await message.reply(
            files=[discord.File(f, filename=os.path.basename(f)) for f in batch],
            mention_author=False,
        )
    if skipped:
        await message.reply(
            f"⚠️ {len(skipped)} item(s) skipped — larger than Discord's {DISCORD_FILE_LIMIT_MB} MB limit.",
            mention_author=False,
        )


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

    try:
        await message.edit(suppress=True)
    except discord.Forbidden:
        pass

    async with message.channel.typing():
        for match in tiktok_matches:
            tiktok_url = match.group(0)
            with tempfile.TemporaryDirectory() as tmpdir:
                files = await download_tiktok(tiktok_url, tmpdir)
                if not files:
                    await message.reply(
                        "Could not download that TikTok. It may be private or region-locked.",
                        mention_author=False,
                    )
                    continue
                await send_media(message, files)

        for match in insta_matches:
            insta_url = match.group(0)
            with tempfile.TemporaryDirectory() as tmpdir:
                files = await download_instagram(insta_url, tmpdir)
                if not files:
                    await message.reply(
                        "Could not download that post. It may be private.",
                        mention_author=False,
                    )
                    continue
                await send_media(message, files)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable.")
    webserver.keep_alive()
    client.run(TOKEN)
