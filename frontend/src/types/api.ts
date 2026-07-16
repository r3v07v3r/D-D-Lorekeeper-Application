// Mirrors backend/app/schemas.py and the response models in
// backend/app/routers/*.py. Kept as plain interfaces (no runtime validation)
// since this is a trusted, single-machine local backend we control.

export type Role = 'gm' | 'player'

export interface UserPublic {
  id: number
  username: string
  role: Role
  discord_id: string | null
  dnd_beyond_character_id: string | null
  total_seconds_active: number
}

export interface LoginResponse {
  token: string
  user: UserPublic
}

export interface CampaignPublic {
  id: number
  name: string
  created_at: string
}

export interface SessionLogPublic {
  id: number
  campaign_id: number
  campaign_name: string
  session_number: number
  date: string
  full_transcript: string | null
  gm_summary: string | null
  player_summary: string | null
  processing_status: 'pending' | 'processing' | 'complete' | 'error'
  processing_error: string | null
}

export interface NotePublic {
  id: number
  session_id: number
  author_id: number
  content: string
  is_private_gm: boolean
  target_player_id: number | null
}

export interface InventoryItemPublic {
  name: string
  quantity: number
  equipped: boolean
}

export interface SpellSlotInfo {
  current: number
  max: number
}

export interface KnownSpell {
  name: string
  level: number // 0 = cantrip
  description: string
}

export interface CharacterPublic {
  source: 'manual' | 'dndbeyond'
  character_id: string
  name: string
  race: string
  classes: string[]
  level: number
  proficiency_bonus: number
  ability_scores: Record<string, number>
  ability_modifiers: Record<string, number>
  hp_current: number
  hp_max: number
  hp_temp: number
  armor_class: number
  armor_class_is_estimate: boolean
  passive_perception: number
  passive_perception_is_estimate: boolean
  currencies: Record<string, number>
  inventory: InventoryItemPublic[]
  spell_slots: Record<string, SpellSlotInfo>
  known_spells: KnownSpell[]
}

// Manual character create/edit payload - see backend/app/routers/characters.py:CharacterInput.
export interface CharacterInput {
  name: string
  race: string
  classes: string[]
  level: number
  proficiency_bonus: number
  ability_scores: Record<string, number>
  hp_current: number
  hp_max: number
  hp_temp: number
  armor_class: number
  passive_perception: number
  currencies: Record<string, number>
  inventory: InventoryItemPublic[]
  spell_slots: Record<string, SpellSlotInfo>
  known_spells: KnownSpell[]
}

export interface PartyMemberPublic {
  user_id: number
  username: string
  character: CharacterPublic | null
  sync_error: string | null
}

export interface BotStatusResponse {
  connected: boolean
  is_recording: boolean
  current_session_log_id: number | null
}

export interface SetupItem {
  key: string
  severity: 'required' | 'optional'
  message: string
}

export interface SettingsPublic {
  discord_bot_token_set: boolean
  openai_api_key_set: boolean
  whisper_model: string
  summarization_model: string
  llm_provider: string
  ollama_base_url: string
  transcription_provider: string
  local_whisper_model_size: string
  recording_chunk_minutes: number
  dndbeyond_sync_interval_minutes: number
  bot_running: boolean
  campaign_passphrase_set: boolean
  detected_lan_ip: string | null
  detected_public_ip: string | null
  certificate_fingerprint: string
  server_port: number
  setup_items: SetupItem[]
}

export interface SettingsUpdate {
  discord_bot_token?: string
  openai_api_key?: string
  whisper_model?: string
  summarization_model?: string
  llm_provider?: string
  ollama_base_url?: string
  transcription_provider?: string
  local_whisper_model_size?: string
  recording_chunk_minutes?: number
  dndbeyond_sync_interval_minutes?: number
  campaign_passphrase?: string
}

export interface SoundClipPublic {
  id: number
  name: string
  volume: number
  created_at: string
}

export interface SoundClipUpload {
  name: string
  filename: string
  content_base64: string
  volume?: number
}

export interface SoundClipUpdate {
  name?: string
  volume?: number
}

export interface SoundClipAudio {
  content_base64: string
  mime_type: string
}
