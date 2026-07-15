// Encodes/decodes the GM's "share code": a single paste-able string a
// player uses instead of typing in an IP, port, passphrase, and
// certificate fingerprint separately.
//
// This is base64-encoded JSON, not a hash. A SHA/MD5 hash is one-way - you
// cannot get the IP/port back out of one, which is the whole point of a
// share code (the player's app needs to *recover* that information, not
// just verify it against something). Base64 just makes the JSON blob safe
// to paste into a text field/chat message without special characters
// causing problems; it provides no confidentiality by itself; whoever has
// the code can decode it, so a share code should be treated like the
// passphrase itself - shared with your players, not posted publicly.
export interface ShareCodePayload {
  v: 1
  publicIp: string | null
  lanIp: string | null
  port: number
  passphrase: string
  fingerprint: string
}

function utf8ToBase64(str: string): string {
  return btoa(unescape(encodeURIComponent(str)))
}

function base64ToUtf8(b64: string): string {
  return decodeURIComponent(escape(atob(b64)))
}

export function encodeShareCode(payload: ShareCodePayload): string {
  return utf8ToBase64(JSON.stringify(payload))
}

export function decodeShareCode(code: string): ShareCodePayload {
  let parsed: unknown
  try {
    parsed = JSON.parse(base64ToUtf8(code.trim()))
  } catch {
    throw new Error('That share code looks corrupted - ask your GM for a fresh one.')
  }

  if (
    typeof parsed !== 'object' ||
    parsed === null ||
    !('port' in parsed) ||
    !('fingerprint' in parsed) ||
    !('passphrase' in parsed)
  ) {
    throw new Error('That share code looks corrupted - ask your GM for a fresh one.')
  }

  return parsed as ShareCodePayload
}
