// Thin request wrapper. The bearer token is passed in explicitly by callers
// (via useAuth()) rather than read from a module-level global, so there's
// one obvious place (AuthContext) that owns the token's lifecycle.
//
// The base URL and campaign passphrase are read fresh from serverConfig on
// every call (not cached at import time), so switching servers via the
// "Connect to a server" screen takes effect immediately without a reload.
//
// Requests go through window.lorekeeper.apiRequest (Electron's main
// process, over IPC) when it's available, since the backend serves HTTPS
// with a self-signed certificate that only the main process knows how to
// validate via fingerprint pinning (see electron/main.js). In a plain
// browser tab (no Electron - e.g. this frontend loaded directly against a
// dev backend for testing), window.lorekeeper is undefined and this falls
// back to plain fetch(); connecting to a self-signed HTTPS backend that way
// requires manually accepting the browser's certificate warning once.
import { getServerConfig } from './serverConfig'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(
  path: string,
  options: { method?: string; token?: string | null; body?: unknown } = {},
): Promise<T> {
  const { baseUrl, passphrase } = getServerConfig()
  const method = options.method ?? (options.body !== undefined ? 'POST' : 'GET')

  const headers: Record<string, string> = {}
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (options.token) headers['Authorization'] = `Bearer ${options.token}`
  // Harmless to send on every request - only the two endpoints reachable
  // without a session token (GET /users, POST /auth/login) actually check
  // it (see backend/app/auth.py require_network_access).
  if (passphrase) headers['X-Campaign-Passphrase'] = passphrase

  const url = `${baseUrl}${path}`
  const body = options.body !== undefined ? JSON.stringify(options.body) : undefined

  let status: number
  let responseText: string

  if (window.lorekeeper) {
    const result = await window.lorekeeper.apiRequest({ url, method, headers, body })
    if (result.error) throw new ApiError(0, result.error)
    status = result.status
    responseText = result.body
  } else {
    const response = await fetch(url, { method, headers, body })
    status = response.status
    responseText = await response.text()
  }

  if (status < 200 || status >= 300) {
    let detail = `HTTP ${status}`
    try {
      const errorBody = JSON.parse(responseText)
      detail = errorBody.detail ?? detail
    } catch {
      // response had no JSON body - fall back to the generic message
    }
    throw new ApiError(status, detail)
  }

  if (status === 204 || status === 202 || !responseText) {
    return undefined as T
  }
  return JSON.parse(responseText) as T
}

export const api = {
  get: <T>(path: string, token?: string | null) => request<T>(path, { method: 'GET', token }),
  post: <T>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: 'POST', token, body: body ?? {} }),
  put: <T>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: 'PUT', token, body: body ?? {} }),
  patch: <T>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: 'PATCH', token, body: body ?? {} }),
  delete: <T>(path: string, token?: string | null) => request<T>(path, { method: 'DELETE', token }),
}
