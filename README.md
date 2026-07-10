# Discord Voice Channel Announcer Bot

Announces in a text channel whenever someone **joins**, **leaves**, or **switches** a voice channel.

## 1. Create the bot on Discord
1. Go to https://discord.com/developers/applications → **New Application**.
2. Go to the **Bot** tab → **Add Bot** → copy the **Token**.
3. On the same Bot tab, scroll to **Privileged Gateway Intents** and enable:
   - **SERVER MEMBERS INTENT**
   - **PRESENCE INTENT** (not required, but fine to enable)
4. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `View Channels`, `Send Messages`
   - Copy the generated URL and open it in your browser to invite the bot to your server.

## 2. Set up the project
```bash
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env` and paste your bot token:
```
DISCORD_TOKEN=your_bot_token_here
```
(Optional) Set `ANNOUNCE_CHANNEL_ID` to a specific text channel ID if you don't want it using the server's default/system channel.

## 3. Run the bot
```bash
python bot.py
```

You should see:
```
Logged in as YourBotName#1234 (ID: ...)
Bot is ready and watching voice channels.
```

Now join, leave, or switch voice channels in your server — the bot will post messages like:
```
🔊 Ankit joined General
🔀 Ankit moved from General to Gaming
🔇 Ankit left Gaming
```

## Customizing
- **Ignore bots**: already skipped by default (`if member.bot: return` in `bot.py`).
- **Only watch specific voice channels**: add a check on `after.channel.id` / `before.channel.id` against a list of allowed IDs.

---

## Spoken (TTS) version — `bot_voice.py`

This version has the bot **join the voice channel and speak** the announcement out loud (e.g. "Ankit joined the channel") instead of posting text.

### Extra requirements
1. **ffmpeg must be installed on your system** (not just pip) and available on your PATH:
   - Windows: download from https://ffmpeg.org/download.html and add the `bin` folder to PATH
   - macOS: `brew install ffmpeg`
   - Linux (Debian/Ubuntu): `sudo apt install ffmpeg`
2. Install Python dependencies:
   ```bash
   pip install -r requirements_voice.txt
   ```
3. In the Discord Developer Portal, also grant the bot the **Connect** and **Speak** permissions (in addition to View Channels / Send Messages) when generating your invite URL.
4. Use the same `.env` file / `DISCORD_TOKEN` as the text version.

### Run it
```bash
python bot_voice.py
```

### How it behaves
- When someone **joins** a VC, the bot joins that same VC and says "*Name* joined the channel."
- When someone **leaves** a VC (and other people remain in it), the bot says "*Name* left the channel" in that VC.
- When someone **switches** VCs, it announces the leave in the old channel and the join in the new one.
- Announcements are queued per-server so they play one at a time instead of overlapping.
- If there's nothing to announce for 5 seconds, the bot automatically disconnects from voice until needed again.
- Uses `gTTS` (Google Text-to-Speech), which requires an internet connection to generate each audio clip — same as your bot already needs to reach Discord.

### Notes / things you may want to tweak
- **No "left" announcement if the channel becomes empty**: the bot can't audibly announce into an empty room, so leaves are only announced if someone else is still in that channel. You could change this to always join briefly and announce regardless, if you prefer.
- **Rate limits**: gTTS is a free unofficial API — for a very high-traffic server, you might hit throttling. An alternative is `edge-tts` (uses Microsoft Edge's TTS voices, also free) or a paid TTS API for higher reliability.
- **Custom phrasing/voice**: change the `lang` parameter in `gTTS(text=text, lang="en")`, or swap in a different TTS engine, for different accents/languages.
