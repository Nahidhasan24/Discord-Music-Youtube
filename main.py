import discord
from discord.ext import commands
import asyncio
from collections import deque
import os
import logging
import yt_dlp
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)

# Discord bot token from environment
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN not set in environment variables!")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# FFmpeg options
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -nostdin',
}

# Queue for each guild
queues = {}

# YTDLSource class
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title', 'Unknown Title')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            data = await loop.run_in_executor(None, extract)
        except Exception as e:
            return None, f'yt-dlp error: {e}'

        # pick playable audio url
        if 'url' in data:
            audio_url = data['url']
        elif 'formats' in data and len(data['formats']) > 0:
            audio_url = data['formats'][0]['url']
        else:
            return None, 'No playable URL found in yt-dlp output.'

        ffmpeg_source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        return cls(ffmpeg_source, data=data), None

# Play next song in queue
async def play_next(ctx):
    if queues.get(ctx.guild.id) and queues[ctx.guild.id]:
        next_song = queues[ctx.guild.id].popleft()
        player, error = await YTDLSource.from_url(next_song, loop=bot.loop, stream=True)

        if error:
            await ctx.send(f"Skipping song due to error: {error}")
            await play_next(ctx)
            return

        def after_play(error):
            fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_play: {e}")

        ctx.voice_client.play(player, after=after_play)
        await ctx.send(f'Now playing: {player.title}')
    else:
        await ctx.send('Queue is empty. Use `!play <url>` to add songs.')

# Bot events
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

# --- Bot commands ---
@bot.command(name='join')
async def join(ctx):
    if not ctx.author.voice:
        await ctx.send(f'{ctx.author.name}, you are not connected to a voice channel.')
        return
    await ctx.author.voice.channel.connect()

@bot.command(name='leave')
async def leave(ctx):
    if ctx.voice_client:
        queues.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await ctx.send('Left the voice channel 🚪')

@bot.command(name='play')
async def play(ctx, url: str):
    if not ctx.author.voice:
        await ctx.send(f'{ctx.author.name}, you are not connected to a voice channel.')
        return

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = deque()

    queues[ctx.guild.id].append(url)
    await ctx.send(f'Added to queue: {url}')

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command(name='pause')
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('Paused ⏸')

@bot.command(name='resume')
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Resumed ▶')

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
    queues.pop(ctx.guild.id, None)
    await ctx.send('Stopped ⏹')

@bot.command(name='queue')
async def show_queue(ctx):
    if queues.get(ctx.guild.id) and queues[ctx.guild.id]:
        queue_list = '\n'.join([f'{i + 1}. {url}' for i, url in enumerate(queues[ctx.guild.id])])
        await ctx.send(f'Current queue:\n{queue_list}')
    else:
        await ctx.send('The queue is empty.')

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('Skipped ⏭')
        await play_next(ctx)
    else:
        await ctx.send('No song is currently playing.')

# Run bot
bot.run(DISCORD_BOT_TOKEN)
