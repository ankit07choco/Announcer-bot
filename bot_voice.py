"""
Discord Voice Channel Announcer Bot (SPOKEN version)
------------------------------------------------------
When a member joins, leaves, or switches a voice channel, the bot joins
that voice channel and SPEAKS an announcement using text-to-speech
(e.g. "Ankit joined the channel").

Requirements:
  - ffmpeg installed on the system (not just pip) and available on PATH
  - pip install -r requirements_voice.txt

Setup:
  1. pip install -r requirements_voice.txt
  2. Create a .env file (see .env.example) with your bot token
  3. python bot_voice.py
"""

import os
import asyncio
import tempfile
import webserver

import discord
from discord.ext import commands
from dotenv import load_dotenv
from gtts import gTTS

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# One announcement queue + worker task per guild, so overlapping events
# don't try to talk over each other.
guild_queues: dict[int, asyncio.Queue] = {}
guild_workers: dict[int, asyncio.Task] = {}

# How long to wait in an empty voice channel before disconnecting
DISCONNECT_DELAY = 5  # seconds


def make_tts_file(text: str) -> str:
    """Generate an mp3 file for the given text and return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    gTTS(text=text, lang="en").save(tmp.name)
    return tmp.name


async def play_announcement(voice_client: discord.VoiceClient, text: str):
    """Generate TTS audio and play it through the given voice client, waiting until done."""
    loop = asyncio.get_running_loop()
    path = await loop.run_in_executor(None, make_tts_file, text)

    finished = asyncio.Event()

    def after_playing(error):
        if error:
            print(f"Playback error: {error}")
        loop.call_soon_threadsafe(finished.set)

    source = discord.FFmpegPCMAudio(path)
    voice_client.play(source, after=after_playing)
    await finished.wait()

    try:
        os.remove(path)
    except OSError:
        pass


async def guild_worker(guild: discord.Guild):
    """Consumes (channel, text) announcement jobs for a single guild, one at a time."""
    queue = guild_queues[guild.id]
    voice_client: discord.VoiceClient | None = None

    while True:
        try:
            channel, text = await asyncio.wait_for(queue.get(), timeout=DISCONNECT_DELAY)
        except asyncio.TimeoutError:
            # Nothing new to announce for a while — disconnect and end the worker.
            if voice_client and voice_client.is_connected():
                await voice_client.disconnect()
            break

        try:
            if voice_client is None or not voice_client.is_connected():
                voice_client = await channel.connect()
            elif voice_client.channel.id != channel.id:
                await voice_client.move_to(channel)

            await play_announcement(voice_client, text)
        except Exception as e:
            print(f"Error announcing in {guild.name}: {e}")
        finally:
            queue.task_done()

    guild_workers.pop(guild.id, None)


def queue_announcement(guild: discord.Guild, channel: discord.VoiceChannel, text: str):
    if guild.id not in guild_queues:
        guild_queues[guild.id] = asyncio.Queue()

    guild_queues[guild.id].put_nowait((channel, text))

    # Start (or restart) the worker if it isn't running
    existing = guild_workers.get(guild.id)
    if existing is None or existing.done():
        guild_workers[guild.id] = bot.loop.create_task(guild_worker(guild))


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Bot is ready and watching voice channels.")


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.bot:
        return

    guild = member.guild
    name = member.display_name

    # Joined a voice channel
    if before.channel is None and after.channel is not None:
        queue_announcement(guild, after.channel, f"{name} joined the channel")

    # Left a voice channel entirely
    elif before.channel is not None and after.channel is None:
        # Bot can't announce "left" audibly in a channel with no one in it
        # unless it's still connected there — only announce if others remain.
        if len(before.channel.members) > 0:
            queue_announcement(guild, before.channel, f"{name} left the channel")

    # Switched channels
    elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
        if len(before.channel.members) > 0:
            queue_announcement(guild, before.channel, f"{name} left the channel")
        queue_announcement(guild, after.channel, f"{name} joined the channel")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("ERROR: DISCORD_TOKEN not found. Set it in your .env file.")
    webserver.keep_alive()
    bot.run(TOKEN)