// Where this app talks to the backend, the campaign passphrase used to
// authenticate before a session token exists (see backend/app/auth.py
// require_network_access), and - for a remote (non-default) server - the
// certificate fingerprint this app should pin that connection to (see
// electron/main.js). Stored in this browser profile's localStorage - each
// machine (GM's or a player's) keeps its own copy, since each is pointed at
// whichever server it should be, be it itself (hosting) or the GM's
// machine (joining).
const STORAGE_KEY = 'lorekeeper_server_config'

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'https://127.0.0.1:8000'

export interface ServerConfig {
  baseUrl: string
  passphrase: string
  // Only meaningful for a non-default (remote) server - the GM's own
  // default local backend is auto-trusted by electron/main.js without any
  // renderer involvement, since Electron generated it itself moments ago.
  fingerprint: string | null
}

export function getServerConfig(): ServerConfig {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return { baseUrl: DEFAULT_BASE_URL, passphrase: '', fingerprint: null }
  try {
    const parsed = JSON.parse(raw) as Partial<ServerConfig>
    return {
      baseUrl: parsed.baseUrl || DEFAULT_BASE_URL,
      passphrase: parsed.passphrase || '',
      fingerprint: parsed.fingerprint || null,
    }
  } catch {
    return { baseUrl: DEFAULT_BASE_URL, passphrase: '', fingerprint: null }
  }
}

export function setServerConfig(config: ServerConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))

  // Only Electron (not a plain dev-mode browser tab) exposes this - tell
  // the main process which certificate to trust for this connection so its
  // pinned HTTPS client (see electron/main.js) will actually accept it.
  if (config.fingerprint && window.lorekeeper) {
    try {
      const hostKey = new URL(config.baseUrl).host
      window.lorekeeper.trustFingerprint(hostKey, config.fingerprint)
    } catch {
      // malformed baseUrl - the subsequent request will fail with a clear
      // error anyway, nothing useful to do here.
    }
  }
}
