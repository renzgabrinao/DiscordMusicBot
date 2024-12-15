import yt_dlp
import discord
import os
import asyncio

FFMPEG_OPTIONS = {
    "options": "-vn",  # Ignore video streams
}

TEMP_AUDIO_FOLDER = "audio_files"  # Folder to store temporary audio files

# Queue to manage song playback
song_queue = []
preloaded_song = None  # Holds the path to the pre-downloaded song
is_playing = False

# Ensure the folder exists
if not os.path.exists(TEMP_AUDIO_FOLDER):
    os.makedirs(TEMP_AUDIO_FOLDER)


async def download_audio(url, filename):
    """Download audio via yt_dlp and save it with a specific filename."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{TEMP_AUDIO_FOLDER}/{filename}.%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,  # Suppress yt_dlp logs
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
        file_path = f"{TEMP_AUDIO_FOLDER}/{filename}.mp3"
        print(f"Downloaded audio for {url}")
        return file_path
    except Exception as e:
        print(f"Failed to download audio: {e}")
        return None


async def preload_next_song():
    """Download the next song in the queue (if any) in advance."""
    global preloaded_song

    if song_queue:  # Check if there's a next song to preload
        next_song_url = song_queue[0]  # Peek at the next song
        song_filename = f"preload_{int(asyncio.get_event_loop().time())}"

        print("Preloading next song...")
        file_path = await download_audio(next_song_url, song_filename)
        if file_path:
            preloaded_song = file_path
            print(f"Preloaded next song: {preloaded_song}")
        else:
            print("Failed to preload the next song.")


async def play_next(context):
    """Play the next song in the queue."""
    global is_playing, preloaded_song

    if is_playing:
        return  # Don't interrupt an active playback

    if not song_queue:
        await context.send("Queue is empty, playback stopped.")
        is_playing = False
        return

    is_playing = True

    # Use preloaded song if available, else download
    if preloaded_song:
        file_path = preloaded_song
        preloaded_song = None  # Reset preloaded song
    else:
        next_song_url = song_queue.pop(0)
        song_filename = f"song_{int(asyncio.get_event_loop().time())}"
        file_path = await download_audio(next_song_url, song_filename)
        if not file_path:
            await context.send("Failed to download the next song.")
            is_playing = False
            return await play_next(context)

    await context.send(f"Now playing: {file_path}")

    # Play the file
    if context.voice_client:
        loop = asyncio.get_running_loop()
        context.voice_client.play(
            discord.FFmpegPCMAudio(file_path, **FFMPEG_OPTIONS),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                cleanup_and_play_next(context, file_path), loop
            )
        )
        # Preload the next song in the background
        asyncio.create_task(preload_next_song())
    else:
        await context.send("Not connected to a voice channel.")
        is_playing = False


async def cleanup_and_play_next(context, file_path):
    """Deletes the audio file and triggers the next song."""
    global is_playing
    try:
        # Delete the audio file
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")

        # Play the next song
        is_playing = False
        await play_next(context)
    except Exception as e:
        print(f"Error during cleanup: {e}")
