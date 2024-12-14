from discord.ext import commands
import discord
import yt_dlp
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", help_command=None, intents=intents)

TEMP_AUDIO_FILE = "temp_audio"  # Temporary file for downloaded audio

FFMPEG_OPTIONS = {
    "options": "-vn",  # Ignore video streams
}

# Queue to manage song playback
queue = []
is_playing = False


async def download_audio(url):
    """Helper function to download audio via yt_dlp."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{TEMP_AUDIO_FILE}.%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            print("Downloaded audio successfully.")
    except Exception as e:
        print(f"Failed to download audio: {e}")


async def play_next(context):
    """Play the next song in the queue."""
    global is_playing
    if queue:
        next_song = queue.pop(0)
        await download_audio(next_song)

        # Play the downloaded song
        if context.voice_client:
            context.voice_client.play(
                discord.FFmpegPCMAudio(f"{TEMP_AUDIO_FILE}.mp3", **FFMPEG_OPTIONS),
                after=lambda e: asyncio.create_task(play_next(context)) if e is None else None,
            )
            is_playing = True
            await context.send(f"Now playing: {next_song}")
        else:
            await context.send("No voice client available to play the audio.")
    else:
        is_playing = False


@bot.command(name="play")
async def play(context, url: str):
    """Queue a song and start playback if nothing is playing."""
    if not context.author.voice:
        await context.send("You must be in a voice channel to use this command.")
        return

    # Connect to the voice channel if the bot is not already connected
    if not context.voice_client:
        try:
            channel = context.author.voice.channel
            await channel.connect()
        except Exception as e:
            await context.send(f"Failed to connect: {e}")
            return

    # Add the song to the queue
    queue.append(url)
    await context.send(f"Added to queue: {url}")

    # If nothing is currently playing, trigger playback
    global is_playing
    if not is_playing:
        await play_next(context)


@bot.command(name="skip")
async def skip(context):
    """Stop the current song and play the next one in the queue."""
    if context.voice_client and context.voice_client.is_playing():
        context.voice_client.stop()
        await context.send("Skipped to the next track.")
    else:
        await context.send("No audio is currently playing or nothing to skip.")


@bot.command(name="stop")
async def stop(context):
    """Stop playback and clear the queue."""
    if context.voice_client:
        context.voice_client.stop()
        queue.clear()
        global is_playing
        is_playing = False
        await context.send("Stopped playback and cleared the queue.")
    else:
        await context.send("Not connected to any voice channel.")


@bot.command(name="leave")
async def leave(context):
    """Disconnect from the voice channel."""
    if context.voice_client:
        context.voice_client.stop()
        await context.voice_client.disconnect()
        queue.clear()
        global is_playing
        is_playing = False
        await context.send("Disconnected and cleared the queue.")
    else:
        await context.send("Not connected to any voice channel.")


@bot.event
async def on_ready():
    print(f"{bot.user} is connected and ready!")

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
