import discord
import re
import os
import asyncio
import tempfile
import glob
import instaloader
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


def rewrite_tiktok(url: str) -> str:
    return re.sub(r"(?:www\.|m\.)?tiktok\.com", "vxtiktok.com", url, count=1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

L = instaloader.Instaloader(
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    post_metadata_txt_pattern="",
    filename_pattern="{shortcode}",
    quiet=True,
)


async def download_reel(shortcode: str, tmpdir: str) -> str | None:
    loop = asyncio.get_event_loop()

    def _download():
        try:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            L.dirname_pattern = tmpdir
            L.download_post(post, target=tmpdir)
            videos = glob.glob(os.path.join(tmpdir, "**/*.mp4"), recursive=True)
            return videos[0] if videos else None
        except Exception as e:
            print(f"[instaloader error] {e}")
            return None

    return await loop.run_in_executor(None, _download)


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

    # TikTok: URL-rewrite via vxtiktok.com so Discord embeds inline natively.
    # Works even for users in countries where TikTok is blocked.
    for match in tiktok_matches:
        rewritten = rewrite_tiktok(match.group(0))
        await message.reply(rewritten, mention_author=False)

    if not insta_matches:
        return

    async with message.channel.typing():
        for match in insta_matches:
            shortcode = match.group(1)

            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = await download_reel(shortcode, tmpdir)

                if not file_path:
                    await message.reply(
                        "Could not download that reel. It may be private.",
                        mention_author=False,
                    )
                    continue

                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb > 25:
                    await message.reply(
                        f"Reel is too large to upload ({size_mb:.1f} MB, Discord limit is 25 MB).",
                        mention_author=False,
                    )
                    continue

                await message.reply(
                    file=discord.File(file_path, filename="reel.mp4"),
                    mention_author=False,
                )


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("Set the DISCORD_TOKEN environment variable.")
    webserver.keep_alive()
    client.run(TOKEN)
