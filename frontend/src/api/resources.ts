// Typed helpers over api/client.ts, one per backend resource. Keeping these
// separate from the raw client means pages call e.g. listSessions(token)
// instead of stringly-typed api.get('/sessions', token) everywhere.
import { api } from './client'
import type {
  BotStatusResponse,
  CampaignPublic,
  CharacterInput,
  CharacterPublic,
  NotePublic,
  PartyMemberPublic,
  SessionLogPublic,
  SettingsPublic,
  SettingsUpdate,
  SoundClipAudio,
  SoundClipPublic,
  SoundClipUpdate,
  SoundClipUpload,
  UserPublic,
} from '../types/api'

export const listCampaigns = (token: string) => api.get<CampaignPublic[]>('/campaigns', token)
export const createCampaign = (token: string, name: string) =>
  api.post<CampaignPublic>('/campaigns', { name }, token)
export const renameCampaign = (token: string, campaignId: number, name: string) =>
  api.patch<CampaignPublic>(`/campaigns/${campaignId}`, { name }, token)
export const getActiveCampaign = (token: string) => api.get<CampaignPublic | null>('/campaigns/active', token)
export const setActiveCampaign = (token: string, campaignId: number) =>
  api.put<CampaignPublic>('/campaigns/active', { campaign_id: campaignId }, token)

export const listUsers = () => api.get<UserPublic[]>('/users')
export const createPlayer = (
  token: string,
  payload: { username: string; discord_id: string | null; dnd_beyond_character_id: string | null },
) => api.post<UserPublic>('/users', { ...payload, role: 'player' }, token)
// Keyed by user id as a string - JSON object keys are always strings, even
// though the backend's response_model is dict[int, bool] (see
// backend/app/routers/users.py:get_presence).
export const getUserPresence = (token: string) => api.get<Record<string, boolean>>('/users/presence', token)
// Real Discord voice-channel presence (is this user in the same channel as
// the bot right now), distinct from getUserPresence's app-connectivity
// check above - see backend/app/routers/users.py:get_voice_presence.
export const getVoicePresence = (token: string) => api.get<Record<string, boolean>>('/users/voice-presence', token)

export const listSessions = (token: string) => api.get<SessionLogPublic[]>('/sessions', token)
export const getSession = (token: string, id: number) => api.get<SessionLogPublic>(`/sessions/${id}`, token)
export const createSession = (token: string, payload: { session_number: number; date: string }) =>
  api.post<SessionLogPublic>('/sessions', payload, token)
export const processSession = (token: string, id: number) =>
  api.post<{ status: string }>(`/sessions/${id}/process`, undefined, token)

export const listNotes = (token: string, sessionId: number) =>
  api.get<NotePublic[]>(`/sessions/${sessionId}/notes`, token)
export const createNote = (
  token: string,
  sessionId: number,
  payload: { content: string; is_private_gm: boolean; target_player_id: number | null },
) => api.post<NotePublic>(`/sessions/${sessionId}/notes`, payload, token)

export const getMyCharacter = (token: string) => api.get<CharacterPublic>('/characters/me', token)
export const updateMyCharacter = (token: string, payload: CharacterInput) =>
  api.put<CharacterPublic>('/characters/me', payload, token)
export const restCharacter = (token: string) => api.post<CharacterPublic>('/characters/me/rest', undefined, token)
export const getPartyOverview = (token: string) => api.get<PartyMemberPublic[]>('/characters/party', token)
export const triggerCharacterSync = (token: string) =>
  api.post<{ status: string }>('/characters/sync', undefined, token)

export const getBotStatus = (token: string) => api.get<BotStatusResponse>('/bot/status', token)
export const joinVoiceChannel = (token: string, discordChannelId: number) =>
  api.post<void>('/bot/join', { discord_channel_id: discordChannelId }, token)
export const leaveVoiceChannel = (token: string) => api.post<void>('/bot/leave', undefined, token)
export const startRecording = (token: string, sessionLogId: number) =>
  api.post<void>('/bot/record/start', { session_log_id: sessionLogId }, token)
export const stopRecording = (token: string) => api.post<void>('/bot/record/stop', undefined, token)

export const getSettings = (token: string) => api.get<SettingsPublic>('/settings', token)
export const updateSettings = (token: string, payload: SettingsUpdate) =>
  api.put<SettingsPublic>('/settings', payload, token)

export const listSoundClips = (token: string) => api.get<SoundClipPublic[]>('/soundboard', token)
export const uploadSoundClip = (token: string, payload: SoundClipUpload) =>
  api.post<SoundClipPublic>('/soundboard', payload, token)
export const updateSoundClip = (token: string, clipId: number, payload: SoundClipUpdate) =>
  api.patch<SoundClipPublic>(`/soundboard/${clipId}`, payload, token)
export const deleteSoundClip = (token: string, clipId: number) => api.delete<void>(`/soundboard/${clipId}`, token)
export const playSoundClip = (token: string, clipId: number) =>
  api.post<void>(`/soundboard/${clipId}/play`, undefined, token)
export const stopSoundClip = (token: string) => api.post<void>('/soundboard/stop', undefined, token)
export const getSoundClipAudio = (token: string, clipId: number) =>
  api.get<SoundClipAudio>(`/soundboard/${clipId}/audio`, token)
