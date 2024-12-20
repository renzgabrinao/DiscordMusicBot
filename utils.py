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
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            await asyncio.to_thread(ydl.download, [url])

        title = video_info.get("title", "Unknown Title")
        file_path = f"{TEMP_AUDIO_FOLDER}/{filename}.mp3"
        print(f"Downloaded audio for {title} @ {url}")
        return file_path, title
    except Exception as e:
        print(f"Failed to download audio: {e}")
        return None, None


async def preload_next_song():
    """Preload the next song in the queue."""
    global preloaded_song, preloaded_title

    if song_queue:  # Check if there's a next song to preload
        next_song_url = song_queue[0]  # Peek at the next song
        song_filename = f"preload_{int(asyncio.get_event_loop().time())}"

        print("Preloading next song...")
        file_path, title = await download_audio(next_song_url, song_filename)
        if file_path:
            preloaded_song = file_path
            preloaded_title = title
            print(f"Preloaded next song: {title}")
        else:
            print("Failed to preload the next song.")
    else:
        preloaded_song = None
        preloaded_title = None


async def play_next(context):
    """Play the next song in the queue."""
    global is_playing, preloaded_song, preloaded_title

    if is_playing:
        return

    if not song_queue and not preloaded_song:
        await context.send("Queue is empty, playback stopped.")
        is_playing = False
        return

    is_playing = True

    # Use preloaded song if available
    if preloaded_song:
        file_path = preloaded_song
        title = preloaded_title
        preloaded_song = None
        preloaded_title = None
        song_queue.pop(0)  # Remove the song from the queue after using the preload
    else:
        next_song_url = song_queue.pop(0)
        song_filename = f"song_{int(asyncio.get_event_loop().time())}"
        file_path, title = await download_audio(next_song_url, song_filename)
        if not file_path:
            await context.send("Failed to download the next song.")
            is_playing = False
            return await play_next(context)

    await context.send(f"Now playing: {title}")

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
    """Clean up after a song finishes and play the next one."""
    global is_playing
    try:
        os.remove(file_path)  # Delete the audio file after playback
    except OSError as e:
        print(f"Failed to delete file {file_path}: {e}")

    is_playing = False
    await play_next(context)

