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
import json
import logging

from openai import OpenAI

from app.config import Settings
from app.runtime_config import RuntimeConfigStore

logger = logging.getLogger(__name__)

_HIGHLIGHT_CATEGORIES = {"damage", "kill", "death", "critical", "strange", "other"}


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


_HIGHLIGHTS_SYSTEM_PROMPT = """\
You are an assistant extracting notable moments from a Dungeons & Dragons \
session transcript, to power a short "session highlights" list. Extract \
only things that clearly happened in the transcript - never invent details \
that aren't there.

For each notable moment, classify it as one of: "damage", "kill", "death", \
"critical", "strange", "other". Look for a memorable hit or amount of \
damage dealt, a monster or NPC being killed, a player character going down \
or dying, a critical hit or fumble, or an unusually funny/weird/memorable \
moment worth remembering.

If a list of dice rolls actually logged during this session is provided \
below the transcript, prefer grounding "damage"/"critical" entries in \
those real logged numbers rather than estimating from dialogue alone.

Respond with ONLY a JSON array (no other text, no markdown fence), each \
element shaped like:
{"category": "damage", "description": "one plain sentence"}
If nothing notable happened, respond with an empty array: []
Keep it to at most 8 entries - the most notable moments only.
"""


def generate_highlights(transcript: str, roll_context: str, client: OpenAI, model: str) -> list[dict]:
    """Returns a list of {"category", "description"} dicts - never
    fabricated placeholder content: an empty list means nothing notable
    was extracted (or extraction failed to parse), not "no data available."
    """
    user_content = f"Session transcript:\n\n{transcript}"
    if roll_context:
        user_content += f"\n\nDice rolls actually logged during this session:\n{roll_context}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _HIGHLIGHTS_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return _parse_highlights(response.choices[0].message.content or "[]")


def _parse_highlights(raw: str) -> list[dict]:
    text = raw.strip()
    # Defensive only - the prompt explicitly asks for no markdown fence, but
    # models don't always comply. Not a security boundary, just cheap cleanup.
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            first_line, rest = text.split("\n", 1)
            text = rest if first_line.strip().lower() in ("json", "") else text

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Could not parse highlights JSON from LLM response: %r", raw[:200])
        return []
    if not isinstance(parsed, list):
        return []

    highlights = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        description = item.get("description")
        if category in _HIGHLIGHT_CATEGORIES and isinstance(description, str) and description.strip():
            highlights.append({"category": category, "description": description.strip()})
    return highlights[:8]
