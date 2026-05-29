"""Endpoint HTTP para sincronizar achievements de Steam.

Requiere usuario autenticado vía Firebase (token JWT) Y con cuenta de
Steam vinculada (OpenID 2.0 ya ejecutado en /api/auth/steam/start +
/callback).

Invoca el servicio `achievement_sync` que dispara toda la cascada de
items y stickers definida en `services/achievements.py`.

Traducción de excepciones del servicio a HTTP status codes:

  UserNotLinkedError          -> 400  (steam_not_linked)
  SteamProfilePrivateError    -> 400  (steam_profile_private)
  SteamRateLimitError         -> 503 + Retry-After header
  SteamApiTimeoutError        -> 504
  SteamApiKeyInvalidError     -> 503  (error de config del backend, oculto)
  SteamApiUnavailableError    -> 503
  SteamApiError (catch-all)   -> 502
  UserNotFoundError           -> 404  (defensa; el user está autenticado)
"""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify

from app.api.auth import require_auth
from app.services.achievement_sync import (
    SteamSyncResult,
    UserNotFoundError,
    UserNotLinkedError,
    sync_steam_achievements_for_user,
)
from app.services.steam import (
    SteamApiError,
    SteamApiKeyInvalidError,
    SteamApiTimeoutError,
    SteamApiUnavailableError,
    SteamProfilePrivateError,
    SteamRateLimitError,
)

steam_sync_bp = Blueprint("steam_sync", __name__, url_prefix="/api/me")


@steam_sync_bp.route("/steam-sync", methods=["POST"])
@require_auth
def post_steam_sync():
    """Sincroniza los achievements de Steam del usuario autenticado.

    Body de la petición: vacío. El user_id se infiere del token Firebase
    y el steam_id se resuelve desde users en BD.

    Respuesta 200: JSON con el resumen del sync (achievements nuevos,
    items cascaded, sticker applications). Ver _serialize_sync_result.
    """
    user = g.user

    try:
        result = sync_steam_achievements_for_user(user.id)

    except UserNotLinkedError:
        return (
            jsonify(
                error="steam_not_linked",
                message="Please link your Steam account before syncing.",
                help_url="/api/auth/steam/start",
            ),
            400,
        )

    except SteamProfilePrivateError:
        return (
            jsonify(
                error="steam_profile_private",
                message=(
                    "Your Steam profile is private or does not display achievements. "
                    "Change your profile and/or Game Details privacy to "
                    "'Public' on Steam and try again."
                ),
            ),
            400,
        )

    except SteamRateLimitError:
        response = jsonify(
            error="steam_rate_limited",
            message="Steam is rate-limiting requests; please try again in a minute.",
        )

        response.status_code = 503
        response.headers["Retry-After"] = "60"
        return response

    except SteamApiTimeoutError:
        return (
            jsonify(
                error="steam_timeout",
                message="Steam took too long to respond. Please try again.",
            ),
            504,
        )

    except SteamApiKeyInvalidError as e:
        # Bug de configuración del backend — NO exponer detalles al cliente.
        current_app.logger.error("Steam API key issue: %s", e)
        return (
            jsonify(
                error="steam_misconfigured",
                message="Temporary service error. Please try again later.",
            ),
            503,
        )

    except SteamApiUnavailableError as e:
        current_app.logger.warning("Steam API unavailable: %s", e)
        return (
            jsonify(
                error="steam_unavailable",
                message="Steam is not responding. Please try again later.",
            ),
            503,
        )

    except SteamApiError as e:
        # Catch-all para subclases no mapeadas explícitamente.
        current_app.logger.exception("Unexpected Steam API error")
        return (
            jsonify(
                error="steam_unknown_error",
                message=str(e),
            ),
            502,
        )

    except UserNotFoundError:
        # No debería ocurrir: el user está autenticado vía @require_auth.
        # Lo dejamos por defensa por si alguien borrara el user entre
        # la verificación del token y la query de sync.
        return jsonify(error="user_not_found"), 404

    return jsonify(_serialize_sync_result(result)), 200


def _serialize_sync_result(result: SteamSyncResult) -> dict:
    """Convierte un SteamSyncResult a dict JSON-serializable.

    Expone tanto un bloque `summary` con conteos para mostrar de un
    vistazo, como una lista detallada `newly_unlocked` con cada
    achievement nuevo y sus cascadas, útil para mostrar al usuario
    "has desbloqueado X, que a su vez te ha dado Y, Z".
    """
    return {
        "user_id": result.user_id,
        "steam_id": result.steam_id,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
        "last_steam_sync_at": result.last_steam_sync_at.isoformat(),
        "summary": {
            "steam_achievements_received": result.steam_achievements_received,
            "steam_achievements_achieved": result.steam_achievements_achieved,
            "newly_unlocked_count": result.newly_unlocked_count,
            "already_unlocked_count": result.already_unlocked_count,
            "total_items_cascaded": result.total_items_cascaded,
            "total_sticker_applications": result.total_sticker_applications,
        },
        "newly_unlocked": [
            {
                "id": r.achievement.id,
                "steam_api_name": r.achievement.steam_api_name,
                "name": r.achievement.name,
                "cascaded_items": [
                    {"id": item.id, "name": item.name, "type": item.type.name}
                    for item in r.cascaded_unlockables
                ],
                "cascaded_sticker_count": len(r.cascaded_sticker_applications),
                "notes": r.notes,
            }
            for r in result.unlock_results
            if not r.achievement_was_already_unlocked
        ],
        "unknown_apinames": result.unknown_apinames,
    }
