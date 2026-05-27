"""Servicio de sincronización de achievements desde Steam.

Orquesta el flujo completo:

    [steam.py] ──fetch──> [achievements.py] ──cascade──> [BD]

Por cada achievement desbloqueado en Steam, invoca el servicio existente
``unlock_achievement_by_code(...)`` con ``source=STEAM_SYNC``, que a su
vez aplica la cascada genérica de items con ``unlock_factor`` compartido
y los resolvers especiales (Rule Breaker, Completionist, Completionist+,
Completionist++).

Idempotencia: garantizada por la idempotencia ya existente del servicio
de achievements. Re-ejecutar el sync sin cambios desde Steam es no-op
(devuelve un resultado con `newly_unlocked_count == 0`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from flask import current_app

from app.extensions import db
from app.models import (
    Achievement,
    User,
    UserAchievement,
    UserStickerApplication,
    UserUnlock,
)
from app.models.enums import UnlockSource
from app.services.achievements import (
    UnlockAchievementResult,
    unlock_achievement_by_code,
)
from app.services.steam import (
    SteamAchievement,
    get_player_achievements,
)

# =============================================================================
# Excepciones del servicio
# =============================================================================


class SteamSyncError(Exception):
    """Error base del servicio de sync. Captura este para atrapar todo."""


class UserNotFoundError(SteamSyncError):
    """El user_id no existe en la BD."""


class UserNotLinkedError(SteamSyncError):
    """El usuario no tiene una cuenta de Steam vinculada (steam_id NULL).

    Tratamiento esperado en el endpoint: HTTP 400 con instrucciones de
    vincular la cuenta vía /api/auth/steam/start.
    """


# =============================================================================
# Resultado público
# =============================================================================


@dataclass
class SteamSyncResult:
    """Resumen de un sync de Steam para un usuario.

    Diseñado para ser serializable a JSON desde el endpoint, exponiendo
    suficiente detalle al frontend para mostrar "has desbloqueado X, Y, Z"
    y "se han descubierto N items en cascada".

    Los conteos derivados (newly_unlocked_count, etc.) se calculan vía
    properties para evitar inconsistencias.
    """

    user_id: int
    steam_id: str
    started_at: datetime
    completed_at: datetime
    last_steam_sync_at: datetime

    # Datos crudos de Steam
    steam_achievements_received: int
    steam_achievements_achieved: int

    # Resultados de cada invocación a unlock_achievement_by_code
    unlock_results: list[UnlockAchievementResult] = field(default_factory=list)

    # apinames que Steam reportó pero que no existen en `achievements`
    # (típicamente significa que Balatro añadió un achievement nuevo que
    # nuestro seed aún no cubre — alertar a ops para extender el seed).
    unknown_apinames: list[str] = field(default_factory=list)

    @property
    def newly_unlocked_count(self) -> int:
        """Achievements que pasaron de no-desbloqueado a desbloqueado."""
        return sum(
            1 for r in self.unlock_results if not r.achievement_was_already_unlocked
        )

    @property
    def already_unlocked_count(self) -> int:
        """Achievements que ya estaban desbloqueados antes de este sync."""
        return sum(1 for r in self.unlock_results if r.achievement_was_already_unlocked)

    @property
    def total_items_cascaded(self) -> int:
        """Suma de unlockables desbloqueados via shared-factor + resolvers."""
        return sum(len(r.cascaded_unlockables) for r in self.unlock_results)

    @property
    def total_sticker_applications(self) -> int:
        """Suma de UserStickerApplication creadas/promovidas."""
        return sum(len(r.cascaded_sticker_applications) for r in self.unlock_results)


# =============================================================================
# API pública
# =============================================================================


# Tipo del callable del cliente Steam — sirve para inyección en tests.
SteamClientFn = Callable[..., list[SteamAchievement]]


def sync_steam_achievements_for_user(
    user_id: int,
    *,
    steam_client_fn: SteamClientFn = get_player_achievements,
    when: Optional[datetime] = None,
) -> SteamSyncResult:
    """Sincroniza los achievements de Steam de un usuario contra nuestra BD.

    Flujo:
      1. Verifica que el user existe y tiene steam_id vinculado.
      2. Llama al cliente Steam para obtener los achievements del jugador.
      3. Filtra los `achieved == True`.
      4. Pre-fetcha en una query los Achievements de nuestra BD que
         matchean los apinames recibidos (evita N+1).
      5. Por cada uno, invoca unlock_achievement_by_code con
         source=STEAM_SYNC y when=unlocktime de Steam.
      6. Actualiza users.last_steam_sync.

    Args:
        user_id: id interno del usuario en nuestra BD.
        steam_client_fn: opcional, callable inyectable para tests (default:
            el cliente real ``get_player_achievements``).
        when: opcional, timestamp del sync (default: now(UTC)). El
            ``unlocked_at`` de cada achievement individual usa el
            ``unlocktime`` que reporta Steam (no este timestamp).

    Returns:
        SteamSyncResult con resumen agregado y desglose por achievement.

    Raises:
        UserNotFoundError: si user_id no existe.
        UserNotLinkedError: si user.steam_id es NULL.
        SteamApiError (y subclases): bubble-up del cliente Steam si la
            llamada a la API falla (key inválida, perfil privado, rate
            limit, timeout, etc.).
    """
    started_at = when or datetime.now(timezone.utc)

    # 1. Cargar y validar el usuario
    user = db.session.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"User id={user_id} not found")
    if user.steam_id is None:
        raise UserNotLinkedError(f"User id={user_id} has no Steam account linked")

    # 2. Fetch desde Steam — las excepciones SteamApi* propagan hacia arriba
    steam_achievements = steam_client_fn(user.steam_id)
    steam_achievements_received = len(steam_achievements)

    # 3. Filtrar a solo los desbloqueados (achieved=1 en Steam)
    achieved = [a for a in steam_achievements if a.achieved]

    # 4. Pre-fetch en una sola query para detectar apinames desconocidos
    apinames = [a.apiname for a in achieved]
    if apinames:
        known_apinames = {
            row.steam_api_name
            for row in db.session.query(Achievement.steam_api_name)
            .filter(Achievement.steam_api_name.in_(apinames))
            .all()
        }
    else:
        known_apinames = set()

    # 5. Invocar el servicio de unlock por cada achievement desbloqueado
    unlock_results: list[UnlockAchievementResult] = []
    unknown_apinames: list[str] = []
    for steam_ach in achieved:
        if steam_ach.apiname not in known_apinames:
            unknown_apinames.append(steam_ach.apiname)
            current_app.logger.warning(
                "Steam reported achievement %s for user %s, but it is not "
                "in our achievements table. Consider extending the seed.",
                steam_ach.apiname,
                user_id,
            )
            continue

        # Steam reporta unlocktime en epoch seconds UTC. Si por alguna razón
        # no viniera (puede pasar con achievements no granted con timestamp),
        # caemos al timestamp del propio sync.
        if steam_ach.unlocktime:
            unlock_when = datetime.fromtimestamp(steam_ach.unlocktime, tz=timezone.utc)
        else:
            unlock_when = started_at

        result = unlock_achievement_by_code(
            user_id=user_id,
            steam_api_name=steam_ach.apiname,
            source=UnlockSource.STEAM_SYNC,
            when=unlock_when,
        )
        unlock_results.append(result)

    # 6. Actualizar el timestamp de último sync
    user.last_steam_sync = started_at
    db.session.commit()

    completed_at = datetime.now(timezone.utc)

    return SteamSyncResult(
        user_id=user_id,
        steam_id=user.steam_id,
        started_at=started_at,
        completed_at=completed_at,
        last_steam_sync_at=started_at,
        steam_achievements_received=steam_achievements_received,
        steam_achievements_achieved=len(achieved),
        unlock_results=unlock_results,
        unknown_apinames=unknown_apinames,
    )


# =============================================================================
# Cleanup: borrar progreso heredado de Steam al desvincular la cuenta
# =============================================================================


def clear_steam_sync_progress_for_user(user_id: int) -> dict:
    """Borra todas las filas que vinieron del Steam sync para este usuario.

    Pensado para llamarse cuando el usuario desvincula su Steam: el
    "progreso visible" del usuario debe reflejar (a) lo que ha marcado
    de forma manual + (b) lo que Steam reportó EN ESTE MOMENTO. Sin
    cuenta Steam vinculada, la rama (b) pierde su fuente de verdad y
    debe desaparecer — de lo contrario el usuario podría desvincularse,
    volver a vincularse a OTRA cuenta de Steam, y quedarse con un mix
    inconsistente del progreso de ambas.

    Política:
      - Borra UserAchievement con source=STEAM_SYNC.
      - Borra UserUnlock con source=STEAM_SYNC.
      - Borra UserStickerApplication con source=STEAM_SYNC.
      - Limpia `users.last_steam_sync` (sin cuenta vinculada no tiene
        sentido reportar "última sincronización hace 2h").
      - NO toca las filas con source=MANUAL — esas son decisiones
        conscientes del usuario sobre items que él mismo marcó, y se
        preservan independientemente del estado de la vinculación.

    Idempotente: si no hay filas STEAM_SYNC (usuario que nunca
    sincronizó, o ya hizo cleanup antes), devuelve counts en cero.

    Args:
        user_id: id interno del usuario.

    Returns:
        Dict con conteo de filas borradas por tipo (útil para
        log/reporting):
        {
          "user_achievements": int,
          "user_unlocks": int,
          "user_sticker_applications": int,
        }

    Patrón de uso desde el endpoint de unlink:

        from app.services.achievement_sync import clear_steam_sync_progress_for_user

        @auth_bp.route("/steam/unlink", methods=["POST"])
        @require_auth
        def unlink_steam():
            user = g.user
            # 1) Limpia el progreso heredado de Steam ANTES de tocar el
            #    steam_id (el cleanup necesita poder asociar user_id a
            #    filas, lo cual no requiere steam_id pero es más limpio
            #    hacerlo en este orden).
            cleanup_counts = clear_steam_sync_progress_for_user(user.id)
            current_app.logger.info(
                "Steam unlinked for user=%s, cleanup=%s", user.id, cleanup_counts
            )
            # 2) Borra el steam_id del user.
            user.steam_id = None
            db.session.commit()
            return jsonify(ok=True, cleanup=cleanup_counts)
    """
    deleted_achievements = (
        db.session.query(UserAchievement)
        .filter_by(user_id=user_id, source=UnlockSource.STEAM_SYNC)
        .delete(synchronize_session=False)
    )
    deleted_unlocks = (
        db.session.query(UserUnlock)
        .filter_by(user_id=user_id, source=UnlockSource.STEAM_SYNC)
        .delete(synchronize_session=False)
    )

    # FIX P1: Reseteamos SOLO el progreso aportado por Steam a 0
    updated_stickers = (
        db.session.query(UserStickerApplication)
        .filter_by(user_id=user_id)
        .update({"steam_stake_order": 0}, synchronize_session=False)
    )

    # Cleanup de basurilla: si tras quitar Steam, también tenían manual a 0,
    # la fila ya no hace nada, así que la purgamos.
    db.session.query(UserStickerApplication).filter_by(
        user_id=user_id, manual_stake_order=0, steam_stake_order=0
    ).delete(synchronize_session=False)

    user = db.session.get(User, user_id)
    if user is not None:
        user.last_steam_sync = None

    db.session.commit()

    return {
        "user_achievements": deleted_achievements,
        "user_unlocks": deleted_unlocks,
        "user_sticker_applications_cleared": updated_stickers,
    }
