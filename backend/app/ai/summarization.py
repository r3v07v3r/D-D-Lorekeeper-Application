"""GPT-4o summarization: a GM (uncensored) summary and a player-safe recap
from the same session transcript.

IMPORTANT LIMITATION - read before treating this as a security boundary:
the player_summary's "GM secrets stripped" behavior is a *prompted best
effort* by an LLM, not an enforced guarantee. Unlike Note visibility (Model
B, enforced in SQL in app/routers/notes.py), nothing here verifies the model
actually omitted every secret - a sufficiently subtle plot hook could still
leak through. If a GM needs a hard guarantee that specific information never
reaches players, it belongs in a GM-only Note, not in the hope that the
summarization prompt caught it in the transcript. This limitation should be
surfaced to the GM in the UI (Phase 4), not just documented here.
"""
import logging

from openai import OpenAI

from app.config import Settings
from app.runtime_config import RuntimeConfigStore

logger = logging.getLogger(__name__)


def build_llm_client(settings: "Settings | RuntimeConfigStore") -> OpenAI:
    """Builds the chat-completions client for whichever provider the GM has
    selected. Ollama exposes an OpenAI-compatible /v1 endpoint, so this is
    the *only* place provider-switching needs to happen - everything else
    calling _chat()/generate_*_summary() is unaware of which provider is in
    use. The api_key sent to Ollama is a placeholder; Ollama does not check it.
    """
    if settings.llm_provider == "ollama":
        return OpenAI(api_key="ollama", base_url=settings.ollama_base_url)
    return OpenAI(api_key=settings.openai_api_key)

_GM_SYSTEM_PROMPT = """\
You are an assistant summarizing a Dungeons & Dragons session transcript for \
the Game Master. Produce a thorough, uncensored "Master Summary" covering:
- Key plot developments and player decisions
- NPC interactions, including motivations and secrets that were revealed or hinted at
- Combat outcomes and notable rolls/consequences
- Loose threads and plot hooks for future sessions
Do not omit anything for being a spoiler or a secret - this summary is for the GM only.
Write in clear prose, organized with short headers, not raw bullet transcription.
"""

_PLAYER_SYSTEM_PROMPT = """\
You are an assistant summarizing a Dungeons & Dragons session transcript for \
the players (not the GM). Produce a player-safe "recap" of what their \
characters experienced and could plausibly know, in narrative form.

Rules:
- Only include information the player characters directly witnessed or were told in-fiction.
- Omit GM-only information: hidden NPC identities/motivations not revealed in play, foreshadowing \
not yet discovered by the party, secret rolls, and any twist not yet made known to the characters.
- If genuinely unsure whether something is a secret, leave it out rather than risk a spoiler.
- Write in clear, engaging prose suitable for a "previously on our campaign" recap.
"""


def _chat(client: OpenAI, model: str, system_prompt: str, transcript: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Session transcript:\n\n{transcript}"},
        ],
    )
    return response.choices[0].message.content or ""


def generate_gm_summary(transcript: str, client: OpenAI, model: str) -> str:
    return _chat(client, model, _GM_SYSTEM_PROMPT, transcript)


def generate_player_summary(transcript: str, client: OpenAI, model: str) -> str:
    return _chat(client, model, _PLAYER_SYSTEM_PROMPT, transcript)
