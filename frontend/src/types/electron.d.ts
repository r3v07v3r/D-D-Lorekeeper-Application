// Describes the narrow bridge electron/preload.js exposes. Only present
// when running inside the packaged/dev Electron app - undefined in a plain
// browser tab (e.g. this frontend loaded directly in a dev-mode browser for
// testing), which api/client.ts falls back to plain fetch() for.
export interface LorekeeperApiRequest {
  url: string
  method: string
  headers: Record<string, string>
  body?: string
}

export interface LorekeeperApiResponse {
  status: number
  body: string
  error?: string
}

export interface LorekeeperBridge {
  apiRequest: (payload: LorekeeperApiRequest) => Promise<LorekeeperApiResponse>
  trustFingerprint: (hostKey: string, fingerprint: string) => void
}

declare global {
  interface Window {
    lorekeeper?: LorekeeperBridge
  }
}
