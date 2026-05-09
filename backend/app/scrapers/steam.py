"""Cliente de la Steam Web API para Balatro.

Encapsula las llamadas a la API oficial de Steam para extraer datos del
juego (App ID 2379780). A diferencia del módulo wiki, las llamadas aquí
requieren una API key válida configurada en el entorno (``STEAM_API_KEY``).

Funcionalidades actuales:
  - ``fetch_game_achievements_schema()``: obtiene los 31 achievements
    oficiales con nombres, descripciones e iconos. No requiere SteamID.

Pendientes para ramas futuras:
  - ``fetch_player_achievements(steamid)`` para sincronización individual
    cuando integremos el login con Steam OpenID.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
#  Constantes
# ──────────────────────────────────────────────────────────────────────

STEAM_API_BASE_URL = "https://api.steampowered.com"
BALATRO_APPID = 2379780
REQUEST_TIMEOUT_S = 15


# ──────────────────────────────────────────────────────────────────────
#  Excepciones específicas
# ──────────────────────────────────────────────────────────────────────


class SteamAPIError(Exception):
    """Error genérico al comunicarse con la Steam Web API."""


class SteamAPIKeyMissing(SteamAPIError):
    """``STEAM_API_KEY`` no está configurada en el entorno."""


# ──────────────────────────────────────────────────────────────────────
#  Cliente
# ──────────────────────────────────────────────────────────────────────


def _get_api_key() -> str:
    """Devuelve la STEAM_API_KEY del entorno o lanza si no está presente.

    Lectura defensiva: trata cadena vacía o solo espacios como "no
    configurada", igual que hicimos con ``WIKI_USER_AGENT``.
    """
    key = (os.getenv("STEAM_API_KEY") or "").strip()
    if not key:
        raise SteamAPIKeyMissing(
            "STEAM_API_KEY no está configurada en .env. "
            "Obtén una en https://steamcommunity.com/dev/apikey y "
            "añádela a backend/.env antes de continuar."
        )
    return key


def fetch_game_achievements_schema(
    appid: int = BALATRO_APPID,
    language: str = "english",
) -> list[dict[str, Any]]:
    """Obtiene el schema de achievements de un juego desde Steam.

    Llama al endpoint público ``ISteamUserStats/GetSchemaForGame/v2/``,
    que devuelve la lista canónica de achievements definidos por el
    desarrollador (no requiere conocer ningún usuario). Cada elemento de
    la lista tiene la forma::

        {
            "name": "BAL_01",                      # ID interno estable
            "displayName": "Ante Up!",             # nombre visible
            "hidden": 0,                           # 0 = visible, 1 = oculto
            "description": "Reach Ante 4",
            "icon": "https://.../unlocked.jpg",
            "icongray": "https://.../locked.jpg",
        }

    Args:
        appid: AppID del juego. Por defecto Balatro (2379780).
        language: Idioma de los textos. Por defecto ``"english"``.

    Returns:
        Lista de achievements; vacía si Steam no devuelve ninguno.

    Raises:
        SteamAPIKeyMissing: si STEAM_API_KEY no está configurada.
        SteamAPIError: si Steam devuelve error HTTP o JSON inválido.
    """
    key = _get_api_key()
    url = f"{STEAM_API_BASE_URL}/ISteamUserStats/GetSchemaForGame/v2/"

    try:
        response = requests.get(
            url,
            params={"key": key, "appid": appid, "l": language},
            timeout=REQUEST_TIMEOUT_S,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            raise SteamAPIError(
                "Steam API rejected the request (HTTP 403). "
                "Verifica que STEAM_API_KEY es válida y está activa."
            ) from e
        raise SteamAPIError(
            f"Steam API returned HTTP {e.response.status_code}: {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise SteamAPIError(f"Network error contacting Steam API: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise SteamAPIError(
            f"Steam API returned non-JSON response: {e}"
        ) from e

    achievements = (
        data.get("game", {})
        .get("availableGameStats", {})
        .get("achievements", [])
    )

    logger.info(
        "Steam API returned %d achievements for AppID %d",
        len(achievements),
        appid,
    )
    return achievements