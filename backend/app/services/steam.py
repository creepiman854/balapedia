"""Cliente HTTP para la Steam Web API.

Wrapper sobre el endpoint ISteamUserStats/GetPlayerAchievements/v1/ que
necesitamos para sincronizar el progreso de achievements de un usuario
contra Balatro (app_id 2379780).

Diseño:
  - Una sola función pública: ``get_player_achievements(steam_id, app_id=None)``.
  - Si app_id es None, usa ``current_app.config["STEAM_APP_ID"]`` (Balatro).
  - Errores HTTP traducidos a excepciones de dominio descriptivas para
    que el caller pueda discriminar entre "perfil privado" (recuperable
    pidiendo al usuario que ajuste su privacidad), "key inválida" (error
    de configuración del backend), "rate limit" (retry con backoff), etc.
  - Timeout explícito (default 15s) para no colgar workers.

NO se hace caching aquí: la decisión de cuándo refrescar pertenece al
sync service, que tiene contexto sobre ``users.last_steam_sync``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests
from flask import current_app

STEAM_API_BASE = "https://api.steampowered.com"
GET_PLAYER_ACHIEVEMENTS_PATH = "/ISteamUserStats/GetPlayerAchievements/v1/"

# Default timeout en segundos; permite override por argumento para tests.
DEFAULT_TIMEOUT = 15.0


# =============================================================================
# Modelo de datos público
# =============================================================================


@dataclass(frozen=True)
class SteamAchievement:
    """Representación normalizada de un achievement devuelto por Steam.

    `apiname` es el identificador estable que mapea 1:1 contra
    `achievements.steam_api_name` en nuestra BD (BAL_01..BAL_31 para Balatro).
    `unlocktime` es epoch seconds (UTC); None si el achievement no está
    desbloqueado o si Steam no lo reportó.
    """

    apiname: str
    achieved: bool
    unlocktime: Optional[int]


# =============================================================================
# Jerarquía de excepciones
# =============================================================================


class SteamApiError(Exception):
    """Error base del cliente Steam. Captura este si quieres atrapar todo."""


class SteamApiKeyInvalidError(SteamApiError):
    """STEAM_API_KEY no configurada o rechazada por Steam (401/403 sin
    indicio de perfil privado).

    Tratamiento esperado: error de configuración del backend, alertar
    a ops, NO mostrar detalles al usuario final.
    """


class SteamProfilePrivateError(SteamApiError):
    """El perfil del usuario es privado o restringe ver los achievements.

    Tratamiento esperado: pedir al usuario que cambie la privacidad del
    perfil / Game Details a "Public" desde Steam.
    """


class SteamRateLimitError(SteamApiError):
    """Steam respondió con HTTP 429.

    Tratamiento esperado: backoff exponencial; en el endpoint, devolver
    503 al cliente con un Retry-After razonable.
    """


class SteamApiTimeoutError(SteamApiError):
    """La request a Steam superó el timeout configurado."""


class SteamApiUnavailableError(SteamApiError):
    """Steam devolvió 5xx, JSON malformado, o un error de red distinto
    al timeout. Caso degenerado del backend de Steam."""


# =============================================================================
# API pública
# =============================================================================


def get_player_achievements(
    steam_id: str,
    app_id: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[SteamAchievement]:
    """Recupera los achievements de un jugador para un juego dado.

    Args:
        steam_id: SteamID64 del jugador (string de 17 dígitos).
        app_id: ID del juego en Steam. Default = ``config["STEAM_APP_ID"]``
            (Balatro = 2379780).
        timeout: timeout HTTP en segundos.

    Returns:
        Lista de SteamAchievement. Vacía si el juego no tiene achievements
        o si el jugador no ha jugado nunca (Steam devuelve success=true
        con un array vacío en ese caso).

    Raises:
        SteamApiKeyInvalidError: STEAM_API_KEY no configurada o rechazada.
        SteamProfilePrivateError: perfil privado o restringido.
        SteamRateLimitError: throttling por parte de Steam.
        SteamApiTimeoutError: timeout en la request.
        SteamApiUnavailableError: 5xx, malformed JSON, o error de red.
    """
    api_key = current_app.config.get("STEAM_API_KEY")
    if not api_key:
        raise SteamApiKeyInvalidError("STEAM_API_KEY not configured in backend")

    if app_id is None:
        app_id = current_app.config.get("STEAM_APP_ID")
        if app_id is None:
            raise SteamApiError("STEAM_APP_ID not configured in backend")

    params = {
        "key": api_key,
        "steamid": steam_id,
        "appid": app_id,
    }
    url = f"{STEAM_API_BASE}{GET_PLAYER_ACHIEVEMENTS_PATH}"

    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.Timeout as e:
        raise SteamApiTimeoutError(f"Steam API timeout after {timeout}s") from e
    except requests.RequestException as e:
        raise SteamApiUnavailableError(f"Steam API network error: {e}") from e

    # Steam devuelve 401 con key bad o 403 con perfil privado.
    # Discriminamos por el body, porque el status code es ambiguo.
    if response.status_code in (401, 403):
        body_lower = (response.text or "").lower()
        if "profile is not public" in body_lower or "private" in body_lower:
            raise SteamProfilePrivateError(
                f"Profile {steam_id} is private or hides achievements"
            )
        raise SteamApiKeyInvalidError(
            f"Steam rejected the API key (HTTP {response.status_code})"
        )

    if response.status_code == 429:
        raise SteamRateLimitError("Steam API rate limit exceeded")

    if response.status_code >= 500:
        raise SteamApiUnavailableError(
            f"Steam API returned HTTP {response.status_code}"
        )

    if response.status_code != 200:
        # Cualquier otro código inesperado lo tratamos como unavailable.
        raise SteamApiUnavailableError(
            f"Steam API returned unexpected HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except ValueError as e:
        raise SteamApiUnavailableError("Steam API returned malformed JSON") from e

    playerstats = data.get("playerstats") or {}

    if not playerstats.get("success", False):
        # Algunos errores semánticos llegan con HTTP 200 y success=false.
        # Steam usa redacciones distintas para el mismo caso de perfil privado:
        #   "profile is private", "Profile is not public", etc.
        # Aceptamos ambas variantes para no clasificarlas como error genérico.
        error_msg = playerstats.get("error", "unknown error")
        lower_msg = error_msg.lower()
        if "profile" in lower_msg and (
            "private" in lower_msg or "not public" in lower_msg
        ):
            raise SteamProfilePrivateError(
                f"Profile {steam_id} is private: {error_msg}"
            )
        raise SteamApiError(f"Steam API returned success=false: {error_msg}")

    raw_achievements = playerstats.get("achievements", [])
    return [
        SteamAchievement(
            apiname=item["apiname"],
            achieved=bool(item.get("achieved", 0)),
            unlocktime=item.get("unlocktime") or None,
        )
        for item in raw_achievements
    ]
