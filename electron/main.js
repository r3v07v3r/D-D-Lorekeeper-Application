// Electron main process: spawns the Python backend (compiled with
// PyInstaller in production, or the dev venv's interpreter in development),
// waits for it to come up, then loads the React dashboard.
//
// The backend serves HTTPS with a self-signed certificate (see
// backend/app/tls.py) rather than plain HTTP, so a campaign passphrase and
// session tokens are never sent in the clear once players are connecting
// over the internet, not just a LAN. Since there's no CA trust for a
// self-signed cert, this process does the actual HTTP(S) requests itself
// (not the renderer's fetch()) using Node's https module, and manually
// verifies the live certificate's SHA-256 fingerprint against whichever
// fingerprint the renderer has told it to trust for that server - either
// this machine's own backend (registered automatically below) or a remote
// GM's server (registered from a pasted share code - see preload.js /
// frontend/src/api/serverConfig.ts). This is the same trust model as SSH
// host key checking: a mismatch means the connection is refused outright,
// never silently downgraded to "trust anything".
const { app, BrowserWindow, dialog, shell, ipcMain } = require('electron')
const { autoUpdater } = require('electron-updater')
const path = require('node:path')
const fs = require('node:fs')
const https = require('node:https')
const http = require('node:http')
const crypto = require('node:crypto')
const { spawn, execFile } = require('node:child_process')

const BACKEND_PORT = 8000
const LOCAL_BACKEND_URL = `https://127.0.0.1:${BACKEND_PORT}`

let backendProcess = null
let mainWindow = null
let upnpGateway = null // set if a router mapping succeeds - unmapped on quit

// hostKey ("host:port") -> expected certificate SHA-256 fingerprint, colon-
// hex uppercase (Node's tls.TLSSocket#getPeerCertificate().fingerprint256
// format). Populated for this machine's own backend once it's confirmed
// healthy, and for whichever remote server the renderer connects to.
const trustedFingerprints = new Map()

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

function backendConfigDir() {
  return app.isPackaged ? app.getPath('userData') : path.join(__dirname, '..', 'backend')
}

function startBackend() {
  const configDir = backendConfigDir()
  fs.mkdirSync(configDir, { recursive: true })

  if (app.isPackaged) {
    backendProcess = spawn(backendExecutablePath(), [], {
      env: {
        ...process.env,
        LOREKEEPER_PORT: String(BACKEND_PORT),
        LOREKEEPER_CONFIG_DIR: configDir,
        DATABASE_URL: toSqliteUrl(path.join(configDir, 'lorekeeper.db')),
        AUDIO_STORAGE_DIR: path.join(configDir, 'recordings'),
      },
    })
  } else {
    // Development: run straight from source using the backend's own venv
    // interpreter, so `npm start` here doesn't require a separately
    // running backend process.
    const venvPython =
      process.platform === 'win32'
        ? path.join(configDir, 'venv', 'Scripts', 'python.exe')
        : path.join(configDir, 'venv', 'bin', 'python')
    backendProcess = spawn(venvPython, ['run.py'], {
      cwd: configDir,
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
      // rejectUnauthorized: false here only because this is polling our own
      // just-spawned local process purely to learn "is it listening yet" -
      // no credentials or app data are sent on this request, and real trust
      // (registerLocalTrust) is established separately right after this
      // resolves, before the renderer ever talks to the backend.
      const req = https.get(`${LOCAL_BACKEND_URL}/health`, { rejectUnauthorized: false }, (res) => {
        res.resume()
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

// Reads the certificate the backend just generated for itself (see
// backend/app/tls.py) and trusts it for our own loopback connection -
// this is the one case where "trust on first use" is unconditionally safe,
// since we spawned this exact process ourselves moments ago.
function registerLocalTrust() {
  try {
    const certPath = path.join(backendConfigDir(), 'cert.pem')
    const certPem = fs.readFileSync(certPath, 'utf8')
    const cert = new crypto.X509Certificate(certPem)
    trustedFingerprints.set(`127.0.0.1:${BACKEND_PORT}`, cert.fingerprint256)
    console.log('[tls] trusting local backend certificate', cert.fingerprint256)
  } catch (err) {
    console.error('[tls] could not read local certificate for pinning:', err)
  }
}

function checkFfmpegOnPath() {
  return new Promise((resolve) => {
    execFile('ffmpeg', ['-version'], (error) => resolve(!error))
  })
}

// ffmpeg is a required external dependency (project risk #5) - it is not
// and cannot easily be bundled into the app, so this checks for it at every
// launch and, if missing, offers a one-click path to fix it rather than
// just stating the problem.
async function checkFfmpegAndPrompt() {
  const ffmpegOk = await checkFfmpegOnPath()
  if (ffmpegOk) return

  const wingetHint =
    process.platform === 'win32'
      ? 'Quickest fix on Windows: open a terminal (PowerShell or Command Prompt) and run:\n\n    winget install ffmpeg\n\nThen restart Lorekeeper.'
      : process.platform === 'darwin'
        ? 'Quickest fix on macOS (with Homebrew installed): open a terminal and run:\n\n    brew install ffmpeg\n\nThen restart Lorekeeper.'
        : 'Install it with your distribution\'s package manager, e.g.:\n\n    sudo apt install ffmpeg\n\nThen restart Lorekeeper.'

  const { response } = await dialog.showMessageBox({
    type: 'warning',
    title: 'ffmpeg not found',
    message: "Lorekeeper needs ffmpeg for voice recording and transcription, and it wasn't found on your system PATH.",
    detail: `${wingetHint}\n\nThe app will continue to start, but recording and transcription will fail until ffmpeg is installed.`,
    buttons: ['Open ffmpeg.org download page', 'Continue without it'],
    defaultId: 0,
    cancelId: 1,
  })

  if (response === 0) {
    await shell.openExternal('https://ffmpeg.org/download.html')
  }
}

// Best-effort automatic router port-forwarding for internet play, so the GM
// doesn't have to open their router's admin page and configure this by
// hand (see the Settings tab, which always shows the manual steps too -
// this is a convenience layer on top of that, never a replacement for it).
// Deliberately silent on failure: most home routers support UPnP and this
// will just work, but plenty don't (or have it disabled, or the network is
// behind carrier-grade NAT where no port mapping is possible at all) - none
// of that should slow down or interrupt startup. @achingbrain/nat-port-mapper
// is ESM-only, hence the dynamic import() from this CommonJS file.
async function attemptUpnpPortMapping(port) {
  try {
    const { upnpNat } = await import('@achingbrain/nat-port-mapper')
    const client = upnpNat({ description: 'Lorekeeper' })

    for await (const gateway of client.findGateways({ signal: AbortSignal.timeout(8000) })) {
      try {
        for await (const mapping of gateway.mapAll(port, { protocol: 'tcp' })) {
          console.log(`[upnp] mapped port ${port} -> ${mapping.externalHost}:${mapping.externalPort} via router`)
        }
        upnpGateway = gateway
        return
      } catch (err) {
        console.warn('[upnp] found a router but it would not map the port (may not support UPnP):', err.message)
      }
    }
    console.log('[upnp] no UPnP-capable router found on this network - internet play needs manual port forwarding (see Settings)')
  } catch (err) {
    console.warn('[upnp] automatic port mapping unavailable:', err.message)
  }
}

// Performs one HTTP(S) request on behalf of the renderer (invoked over IPC
// from preload.js) and, for HTTPS, manually verifies the live certificate's
// fingerprint against whatever this connection's hostKey was pinned to -
// see the module docstring above for why this can't just rely on normal CA
// trust. Any mismatch is a hard failure: no data is returned to the
// renderer, and the request is treated as failed.
function performRequest({ url, method, headers, body }) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url)
    const isHttps = parsed.protocol === 'https:'
    const lib = isHttps ? https : http
    const hostKey = `${parsed.hostname}:${parsed.port || (isHttps ? 443 : 80)}`
    const expectedFingerprint = trustedFingerprints.get(hostKey)

    if (isHttps && !expectedFingerprint) {
      reject(new Error('No trusted certificate fingerprint on file for this server - refusing to connect.'))
      return
    }

    const req = lib.request(
      // agent: false forces a brand-new socket (and, for HTTPS, a brand-new
      // TLS handshake) for every single request. This was verified to
      // matter, not just a theoretical concern: with Node's default pooling
      // agent, a request could be served over a socket from an earlier
      // connection without re-validating the certificate fresh, which would
      // defeat the pinning check below.
      url,
      { method, headers, rejectUnauthorized: false, agent: false },
      (res) => {
        if (isHttps) {
          const cert = res.socket.getPeerCertificate()
          if (!cert || cert.fingerprint256 !== expectedFingerprint) {
            res.destroy()
            reject(new Error('Server certificate does not match the trusted fingerprint for this connection.'))
            return
          }
        }
        const chunks = []
        res.on('data', (chunk) => chunks.push(chunk))
        res.on('end', () => {
          resolve({
            status: res.statusCode,
            body: Buffer.concat(chunks).toString('utf8'),
          })
        })
      },
    )
    req.on('error', reject)
    if (body) req.write(body)
    req.end()
  })
}

ipcMain.handle('lorekeeper:api-request', async (_event, payload) => {
  try {
    return await performRequest(payload)
  } catch (err) {
    return { status: 0, body: '', error: String(err.message || err) }
  }
})

ipcMain.on('lorekeeper:trust-fingerprint', (_event, hostKey, fingerprint) => {
  trustedFingerprints.set(hostKey, fingerprint)
})

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    // Only needed in dev: `electron .` runs as the generic Electron.exe, so
    // without this the window shows Electron's own icon, not ours. In the
    // packaged app the exe itself already has our icon baked in (via
    // build.win.icon in package.json), which Electron uses as the window
    // icon automatically - build/ isn't bundled as an app resource, so this
    // path wouldn't resolve there anyway.
    icon: app.isPackaged ? undefined : path.join(__dirname, 'assets', 'icon.png'),
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

  await checkFfmpegAndPrompt()

  try {
    await waitForBackend()
    registerLocalTrust()
  } catch (err) {
    dialog.showErrorBox('Backend failed to start', String(err))
  }

  // Fire-and-forget: UPnP discovery can take several seconds and must never
  // delay showing the window.
  attemptUpnpPortMapping(BACKEND_PORT).catch((err) => console.warn('[upnp] unexpected error:', err))

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
  if (upnpGateway) {
    // Best-effort cleanup, same spirit as setting it up - don't leave a
    // stale port-forward rule sitting in the router after the app closes,
    // but don't let a slow/failed unmap delay quitting either.
    upnpGateway.stop().catch(() => {})
    upnpGateway = null
  }
})
