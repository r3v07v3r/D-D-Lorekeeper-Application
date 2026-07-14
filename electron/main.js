// Electron main process: spawns the Python backend (compiled with
// PyInstaller in production, or the dev venv's interpreter in development),
// waits for it to come up, then loads the React dashboard.
const { app, BrowserWindow, dialog } = require('electron')
const { autoUpdater } = require('electron-updater')
const path = require('node:path')
const fs = require('node:fs')
const http = require('node:http')
const { spawn, execFile } = require('node:child_process')

const BACKEND_PORT = 8000
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

let backendProcess = null
let mainWindow = null

function backendExecutablePath() {
  const exeName = process.platform === 'win32' ? 'lorekeeper-backend.exe' : 'lorekeeper-backend'
  return path.join(process.resourcesPath, 'backend', exeName)
}

function frontendIndexPath() {
  return path.join(process.resourcesPath, 'frontend', 'index.html')
}

// SQLAlchemy's sqlite URL wants forward slashes even on Windows.
function toSqliteUrl(filePath) {
  return `sqlite:///${filePath.replace(/\\/g, '/')}`
}

function startBackend() {
  // A stable, per-user, always-writable directory - survives app
  // reinstalls/updates, unlike the versioned install/resources directory.
  // This is where the GM's saved settings (Discord token, OpenAI key - see
  // backend/app/runtime_config.py), the SQLite database, and recordings
  // all live in the packaged app.
  const userDataDir = app.getPath('userData')
  fs.mkdirSync(userDataDir, { recursive: true })

  if (app.isPackaged) {
    backendProcess = spawn(backendExecutablePath(), [], {
      env: {
        ...process.env,
        LOREKEEPER_PORT: String(BACKEND_PORT),
        LOREKEEPER_CONFIG_DIR: userDataDir,
        DATABASE_URL: toSqliteUrl(path.join(userDataDir, 'lorekeeper.db')),
        AUDIO_STORAGE_DIR: path.join(userDataDir, 'recordings'),
      },
    })
  } else {
    // Development: run straight from source using the backend's own venv
    // interpreter, so `npm start` here doesn't require a separately
    // running backend process. Uses the backend's own working directory
    // (via its .env / defaults) rather than userData, so dev data stays
    // separate from anything a packaged install would write.
    const backendDir = path.join(__dirname, '..', 'backend')
    const venvPython =
      process.platform === 'win32'
        ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
        : path.join(backendDir, 'venv', 'bin', 'python')
    backendProcess = spawn(venvPython, ['run.py'], {
      cwd: backendDir,
      env: { ...process.env, LOREKEEPER_PORT: String(BACKEND_PORT) },
    })
  }

  backendProcess.stdout?.on('data', (data) => console.log(`[backend] ${data}`.trimEnd()))
  backendProcess.stderr?.on('data', (data) => console.error(`[backend] ${data}`.trimEnd()))
  backendProcess.on('exit', (code) => {
    console.log(`[backend] exited with code ${code}`)
    backendProcess = null
  })
  backendProcess.on('error', (err) => {
    console.error('[backend] failed to start:', err)
  })
}

function waitForBackend(timeoutMs = 20000) {
  const start = Date.now()
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const req = http.get(`${BACKEND_URL}/health`, (res) => {
        if (res.statusCode === 200) resolve()
        else retry()
      })
      req.on('error', retry)
      req.setTimeout(1000, () => {
        req.destroy()
        retry()
      })
    }
    const retry = () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error('Backend did not become ready in time'))
      } else {
        setTimeout(attempt, 300)
      }
    }
    attempt()
  })
}

function checkFfmpegOnPath() {
  return new Promise((resolve) => {
    execFile('ffmpeg', ['-version'], (error) => resolve(!error))
  })
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (app.isPackaged) {
    await mainWindow.loadFile(frontendIndexPath())
  } else {
    // Vite dev server, started separately (see repo-root .claude/launch.json
    // or `npm run dev` in frontend/).
    await mainWindow.loadURL('http://127.0.0.1:5173')
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(async () => {
  startBackend()

  const [ffmpegOk] = await Promise.all([checkFfmpegOnPath(), Promise.resolve()])
  if (!ffmpegOk) {
    dialog.showErrorBox(
      'ffmpeg not found',
      'Lorekeeper requires ffmpeg to be installed and available on your system PATH ' +
        'for voice recording and transcription to work. The app will continue to start, ' +
        'but recording/transcription features will fail until ffmpeg is installed.',
    )
  }

  try {
    await waitForBackend()
  } catch (err) {
    dialog.showErrorBox('Backend failed to start', String(err))
  }

  await createWindow()

  if (app.isPackaged) {
    autoUpdater.checkForUpdatesAndNotify().catch((err) => console.error('[updater]', err))
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// Stop the spawned backend process before Electron exits, so a quit never
// leaves an orphaned Python process (or an open SQLite file handle) behind.
// Note: on Windows, Node's child_process.kill() always hard-terminates
// (there is no real SIGTERM there), so the backend's own FastAPI shutdown
// handler - which would otherwise close the Discord bot cleanly - does not
// get a chance to run. On macOS/Linux this sends a real SIGTERM, which
// uvicorn traps for a graceful shutdown. Prompting the GM to stop any active
// recording before quitting is the practical mitigation until this is
// worth a proper shutdown handshake.
app.on('will-quit', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
})
