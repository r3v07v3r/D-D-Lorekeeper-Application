// Exposes a small, deliberately narrow API to the renderer: it can ask the
// main process to make one HTTP(S) request (main.js does the actual
// request and certificate-fingerprint verification - see its module
// docstring) and can register which certificate fingerprint to trust for a
// given host:port. No other main-process/Node capability is exposed -
// contextIsolation stays on and nodeIntegration stays off.
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('lorekeeper', {
  apiRequest: (payload) => ipcRenderer.invoke('lorekeeper:api-request', payload),
  trustFingerprint: (hostKey, fingerprint) => ipcRenderer.send('lorekeeper:trust-fingerprint', hostKey, fingerprint),
  openBotPanel: () => ipcRenderer.invoke('lorekeeper:open-bot-panel'),
})
