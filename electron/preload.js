// Intentionally minimal: the renderer talks to the backend purely over HTTP
// (fetch to http://127.0.0.1:8000), so no IPC bridge or exposed Node APIs
// are needed here. contextIsolation stays on and nodeIntegration stays off
// in main.js regardless.
