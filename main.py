from discord.ext import commands
import discord

import os
from dotenv import load_dotenv

from utils import play_next, is_playing, song_queue

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", help_command=None, intents=intents)

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
    song_queue.append(url)
    await context.send(f"Added to queue: {url}")

    global is_playing
    # Only start playback if nothing is currently playing
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
        song_queue.clear()
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
        song_queue.clear()
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
