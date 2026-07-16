# Lorekeeper

An AI-powered campaign companion for Dungeons & Dragons groups that play over Discord.

Lorekeeper joins your Discord voice channel, records each player's audio during a session,
transcribes it with Whisper, and generates two AI summaries: an uncensored **Master Summary**
for the GM and a spoiler-safe **recap** for players. It also keeps GM/player-scoped session
notes, gives the GM a soundboard that plays sound effects into the voice channel, and - if
you choose to link a character - can optionally import and sync live character data (HP,
AC, passive perception, inventory) from D&D Beyond.

The GM runs the app and hosts the campaign; players install the same app on their own
computers and connect to the GM with a one-line **share code**.

Lorekeeper is a standalone, independent application. It is not affiliated with, endorsed
by, or sponsored by D&D Beyond, Wizards of the Coast, or Hasbro. The optional D&D Beyond
sync described below only reads data for characters you already have access to in your
own account - Lorekeeper doesn't store, redistribute, or claim ownership of any D&D Beyond
or Dungeons & Dragons content, and works fully without it if you'd rather build characters
by hand. "D&D Beyond" and "Dungeons & Dragons" are trademarks of their respective owners.

---

## Installing (everyone: GM and players)

1. Download `Lorekeeper-Setup-<version>.exe` from the
   [latest release](https://github.com/R3v07v3R/D-D-Lorekeeper-Application/releases/latest).
   The installer isn't code-signed yet (that costs money and requires identity
   verification from a certificate authority), so expect two separate warnings - neither
   means anything is actually wrong, just that Windows doesn't yet recognize the file:
   - **Your browser** may block the download itself ("Make sure you trust this file...").
     Click the small arrow next to Delete/Cancel and choose **Keep** (Edge) or the
     equivalent "Keep anyway" option (Chrome shows a similar prompt).
   - **Windows** will warn again the first time you run it ("Windows protected your PC").
     Click **More info → Run anyway**.
2. Install **ffmpeg** (required for recording, transcription, and the soundboard).
   The quickest way on Windows is to open a terminal and run:

   ```
   winget install ffmpeg
   ```

   Then restart Lorekeeper. The app checks for ffmpeg at every launch and will point you
   at a download page if it's missing.

On launch, the app checks GitHub Releases for a newer version. If one is available, you'll
be asked whether to update now (downloads and restarts into the new version) or continue
with the version you have - it never updates without asking, and if you say not now you'll
just be asked again next launch.

---

## GM setup (one time)

Every screen but Settings shows a **setup banner** listing anything that still needs
configuring (Discord bot token, an AI provider, etc.) with a one-click link straight to
the right field - use it as a checklist rather than working through this section blind.
Optional items (like a campaign passphrase, only needed to play with others) are called
out separately from the ones that actually block core features.

### 1. Create your profile

On first launch, create the first profile — it becomes the **GM** account.
Add your players from the **Party** tab (with their D&D Beyond character ID and Discord
user ID if you have them).

### 2. Create a Discord bot

The recording bot is *your* bot, running on your machine — you need a (free) Discord
application for it:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   and click **New Application**.
2. Under **Bot**, click **Reset Token** and copy the token.
3. Still under **Bot → Privileged Gateway Intents**, enable **Server Members Intent**.
   ⚠️ This step is required — without it the bot will fail to start even with a valid token.
4. Under **OAuth2 → URL Generator**: check the `bot` scope, then the **Connect**, **Speak**,
   and **View Channels** permissions, and open the generated URL to invite the bot to your
   Discord server.
5. In Lorekeeper: **Settings → Discord Bot Token**, paste the token, save. The bot starts
   immediately — no restart needed.

(This same walkthrough, with clickable links, is also available in-app: **Settings →
"Don't have a bot yet? Show me how to make one"**.)

### 3. Choose transcription and summarization providers

Transcription (turning voice into text) and summarization (turning the transcript into
GM/player recaps) each have a paid, hosted option and a free, local option — pick either
independently in **Settings**:

|                | Paid (hosted)                          | Free (local)                                   |
|----------------|-----------------------------------------|-------------------------------------------------|
| Transcription  | OpenAI Whisper API                      | [faster-whisper](https://github.com/SYSTRAN/faster-whisper), runs on your CPU |
| Summarization  | OpenAI GPT-4o                           | [Ollama](https://ollama.com/download), runs on your CPU |

- **OpenAI (either stage):** create a key at
  [platform.openai.com](https://platform.openai.com/api-keys) and paste it into
  **Settings → OpenAI API Key**. You pay OpenAI directly for what you use; a typical
  multi-hour session costs a few dollars in transcription + summarization.
- **Local Whisper:** pick a model size in **Settings → Transcription** (Small is a good
  default). No account or setup needed — the model downloads automatically the first
  time you transcribe a session and is cached on disk afterward. Slower than the API and
  slightly less accurate, but entirely free and keeps audio on your machine.
- **Ollama:** install [Ollama](https://ollama.com/download), pull a model from a terminal
  (e.g. `ollama pull llama3.1`), then select **Ollama** under **Settings → Summarization**.
  Ollama must be running in the background whenever you summarize a session. Quality
  depends on the model you pick — a small local model won't match GPT-4o, but it's free.

### 4. Let players connect

1. In **Settings**, set a **Campaign Passphrase**. Until one is set, only your own
   computer can log in — this is deliberate.
2. Click **Generate a share code**, re-enter the passphrase, and send the code to your
   players privately (DM, not a public channel — anyone with the code can connect).
3. Players paste it under **"Joining someone else's game?"** on their login screen.

**Same network / same house:** that's it — the share code's LAN address will work.

**Players elsewhere (internet play):** Lorekeeper tries to open port 8000 on your router
automatically (UPnP) every time it starts — if your router supports it, there's nothing
else to do. If not, two options:

- **Port forwarding:** in your router's admin page, forward **TCP port 8000** to your
  computer. The share code already contains your public address; players connect the
  same way. All traffic is encrypted (HTTPS with a pinned certificate), so this is safe
  to expose — but only people with your passphrase can get in.
- **Tailscale (easier, no router changes):** install [Tailscale](https://tailscale.com)
  (free) on your machine and your players', join the same tailnet, and share a code —
  the LAN-style Tailscale address will work like a local connection.

If you ever forget your passphrase, delete `settings.json` from
`%APPDATA%\lorekeeper-electron` and restart the app (your campaign data is untouched —
only settings are reset).

---

## Running a session

The first time you open Lorekeeper (or if you ever click **Switch campaign**), you'll be
asked to pick or create a **campaign** - only a name is required, and it's editable later.
This is what sessions get organized under, and it's the same campaign name your players see
once they connect - useful if you run more than one group, or start a new campaign after an
old one wraps up.

1. **Bot Control** tab → paste your Discord voice channel ID → **Join**.
   (Right-click the voice channel in Discord → *Copy Channel ID*; enable Developer Mode
   in Discord's settings if you don't see that option.)
2. Create a session in the **Sessions** tab, then **Start recording**.
3. Play D&D. Use the **Soundboard** tab to fire sound effects into the channel —
   they play through the bot and don't interrupt recording.
4. **Stop recording** when you're done (before quitting the app, so the last chunk
   flushes to disk).
5. Click **Transcribe + Summarize** on the session. When it finishes, you'll see the
   full speaker-tagged transcript and Master Summary; players see only their recap.

> Note: the player recap's "no spoilers" filtering is done by the AI and is best-effort.
> Anything that must *never* leak to players belongs in a GM-only note, not in the hope
> that the summarizer catches it.

The bot also responds to slash commands in Discord: `/lk_join`, `/lk_leave`,
`/lk_record_start`, `/lk_record_stop`.

---

## Where your data lives

Everything is stored locally on the GM's machine under `%APPDATA%\lorekeeper-electron`:
the SQLite database (`lorekeeper.db`), session recordings (`recordings/`), soundboard
clips, your settings, and the TLS certificate. Back up that folder to back up your
campaign. Nothing is uploaded anywhere except character data fetched from D&D Beyond,
and — only if you've selected the OpenAI provider for a given stage — audio/transcripts
sent to OpenAI for transcription or summarization. Using the local Whisper and Ollama
providers for both stages keeps all session audio and text on your own machine.

---

## Building from source (developers)

Requirements: Python 3.11, Node 20+, ffmpeg on PATH.

```bash
# Backend
cd backend
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # (venv/bin/pip on macOS/Linux)
venv/Scripts/python run.py                     # serves https://0.0.0.0:8000

# Frontend (dev server)
cd frontend
npm install
npm run dev                                    # http://127.0.0.1:5173

# Electron shell (dev: spawns backend + loads the Vite dev server)
cd electron
npm install
npm start
```

Tests: `cd backend && venv/Scripts/pip install -r requirements-dev.txt && venv/Scripts/python -m pytest`

Database migrations use Alembic (`backend/migrations/`). After changing models:
`venv/Scripts/alembic revision --autogenerate -m "describe change"` — migrations run
automatically at app startup, including inside the packaged build.

### Releasing

Releases are built and published automatically by
[`.github/workflows/release.yml`](.github/workflows/release.yml): every push to `main`
checks whether `electron/package.json`'s `version` already has a matching GitHub release,
and if not, runs the backend tests, builds the backend exe + frontend + installer, and
publishes a new release with the installer, `latest.yml`, and `.blockmap` attached (what
the app's auto-updater reads). **Bumping that version is what triggers a release** -
pushes that don't touch it (docs, CI tweaks, etc.) are a no-op.

To build a release locally instead (e.g. to test packaging changes before pushing):

```bash
cd backend  && venv/Scripts/pip install -r requirements-build.txt && venv/Scripts/python build_backend.py
cd frontend && npm run build
cd electron && npx electron-builder --win nsis
```

The installer lands in `electron/dist/`.
