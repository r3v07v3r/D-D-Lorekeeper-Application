"""Fetches raw character JSON from D&D Beyond's (unofficial, undocumented)
character-service API.

Response shape confirmed against a live public character during development:
    {"id": ..., "success": bool, "message": str, "data": {...} | null}

D&D Beyond does not distinguish "character does not exist" from "character
exists but sharing is not set to public" - both return the same
success=false / "The resource requested was not found." response. There is
no way to tell these apart from this endpoint, so the error raised here
covers both cases rather than falsely claiming one or the other.
"""
import httpx

CHARACTER_SERVICE_URL = "https://character-service.dndbeyond.com/character/v5/character/{character_id}"


class DndBeyondError(Exception):
    pass


async def fetch_character_raw(character_id: str) -> dict:
    url = CHARACTER_SERVICE_URL.format(character_id=character_id)
    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            response = await http_client.get(url)
    except httpx.HTTPError as exc:
        raise DndBeyondError(f"Could not reach D&D Beyond: {exc}") from exc

    if response.status_code == 403:
        raise DndBeyondError(
            f"D&D Beyond rejected the request for character {character_id} (403 Unauthorized). "
            f"This almost always means the character's sharing setting isn't 'Public' - on the "
            f"character sheet, open the cog/settings menu and set visibility to Public, then sync again."
        )
    if response.status_code != 200:
        raise DndBeyondError(f"D&D Beyond returned HTTP {response.status_code} for character {character_id}")

    payload = response.json()
    if not payload.get("success"):
        raise DndBeyondError(
            f"D&D Beyond character {character_id} could not be retrieved - it may not exist, "
            f"or its sharing may not be set to public ({payload.get('message', 'no message')})"
        )
    return payload["data"]
