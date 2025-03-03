import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
from collections import deque
from dotenv import load_dotenv
import os
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

# Get the Discord bot token and YouTube cookies from .env
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
YOUTUBE_COOKIES = os.getenv('YOUTUBE_COOKIES')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Suppress noise about console usage from yt-dlp
youtube_dl.utils.bug_reports_message = lambda: ''

# Options for yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': YOUTUBE_COOKIES if YOUTUBE_COOKIES else None,
}

ffmpeg_options = {
    'options': '-vn -nostdin',  # No video and force FFmpeg to exit
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',  # Reconnect on failure
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Queue for each guild
queues = {}

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Function to play the next song in the queue
async def play_next(ctx):
    if queues[ctx.guild.id]:  # Check if there are songs in the queue
        next_song = queues[ctx.guild.id].popleft()  # Get the next song
        player = await YTDLSource.from_url(next_song, loop=bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
        await ctx.send(f'Now playing: {player.title}')
    else:
        await ctx.send('Queue is empty. Use `!play` to add more songs.')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command(name='join', help='Joins the voice channel')
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send(f'{ctx.author.name} is not connected to a voice channel')
        return

    channel = ctx.author.voice.channel
    await channel.connect()

@bot.command(name='leave', help='Leaves the voice channel')
async def leave(ctx):
    if ctx.voice_client:
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()  # Clear the queue
        await ctx.voice_client.disconnect()
        await ctx.send('Left the voice channel 🚪')

@bot.command(name='play', help='Plays a song from YouTube or adds it to the queue')
async def play(ctx, url):
    # Ensure the user is in a voice channel
    if not ctx.author.voice:
        await ctx.send(f'{ctx.author.name} is not connected to a voice channel')
        return

    # Ensure the bot is connected to a voice channel
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    # Initialize the queue for the guild if it doesn't exist
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = deque()

    # Add the song to the queue
    queues[ctx.guild.id].append(url)
    await ctx.send(f'Added to queue: {url}')

    # If the bot is not playing anything, start playing
    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(name='pause', help='Pauses the current song')
async def pause(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('Paused ⏸')

@bot.command(name='resume', help='Resumes the current song')
async def resume(ctx):
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Resumed ▶')

@bot.command(name='stop', help='Stops the current song and clears the queue')
async def stop(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    if ctx.guild.id in queues:
        queues[ctx.guild.id].clear()  # Clear the queue
    await ctx.send('Stopped ⏹')

@bot.command(name='queue', help='Shows the current queue')
async def show_queue(ctx):
    if ctx.guild.id in queues and queues[ctx.guild.id]:
        queue_list = '\n'.join([f'{i + 1}. {url}' for i, url in enumerate(queues[ctx.guild.id])])
        await ctx.send(f'Current queue:\n{queue_list}')
    else:
        await ctx.send('The queue is empty.')

@bot.command(name='skip', help='Skips the current song')
async def skip(ctx):
    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('Skipped ⏭')
        await play_next(ctx)  # Play the next song in the queue
    else:
        await ctx.send('No song is currently playing.')

# Run the bot using the token from .env
bot.run(DISCORD_BOT_TOKEN)