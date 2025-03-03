# YouTube Discord Bot

A feature-rich Discord bot that plays YouTube videos in a voice channel using `yt-dlp` and `FFmpeg`.

## Features

- Play YouTube videos in a voice channel
- Queue system for multiple songs
- Play, pause, resume, skip, and stop controls
- Auto-reconnect on stream failure
- Supports YouTube cookies for restricted content

## Installation

1. Clone the repository:

   ```sh
   git clone https://github.com/Nahidhasan24/Discord-Music-Youtube.git
   ```

2. Install dependencies:

   ```sh
   pip install -r rrequirementstxt
   ```

3. Create a `.env` file and add the following:

   ```ini
   # Discord bot token
   DISCORD_BOT_TOKEN=your_bot_token_here

   # YouTube cookies (optional, for restricted content)
   YOUTUBE_COOKIES=your_youtube_cookies_here
   ```

4. Run the bot:

   ```sh
   python bot.py
   ```

## Commands

- `!join` - Joins the voice channel
- `!leave` - Leaves the voice channel
- `!play <YouTube URL>` - Plays a song from YouTube or adds it to the queue
- `!pause` - Pauses the current song
- `!resume` - Resumes the paused song
- `!stop` - Stops the current song and clears the queue
- `!queue` - Displays the current queue
- `!skip` - Skips the current song and plays the next one

## Requirements

- Python 3.8+
- `discord.py` for bot interaction
- `yt-dlp` for YouTube downloads
- `ffmpeg` for audio processing

## Contributing

Feel free to submit issues or pull requests to improve the bot.

## License

This project is licensed under the MIT License.

