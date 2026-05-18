"""Servicio de progresión de achievements.

Marca un achievement como desbloqueado para un usuario y propaga el efecto
en tres niveles de cascada:

  1. Cascada genérica por shared unlock_factor: cualquier unlockable que
     comparta el `unlock_factor_id` del achievement se marca también como
     desbloqueado (ej. Ante Up! → Showman, Astronomy → Astronomer).

  2. Resolvers especiales con efectos ad-hoc, registrados por
     steam_api_name del achievement:
       - BAL_23 Rule Breaker  → desbloquea TODOS los challenge decks.
       - BAL_29 Completionist → desbloquea TODOS los unlockables con
                                unlock_factor.
       - BAL_30 Completionist+ → aplica Gold Sticker (highest_stake_order=8)
                                 a TODOS los decks.
       - BAL_31 Completionist++ → aplica Gold Sticker a TODOS los jokers
                                  (inferencia: si tienes el achievement,
                                  ya tienes el sticker en cada joker).

  3. (Pendiente para futuras ramas) extensión de la cascada genérica a
     blinds, tags y editions (card_modifiers), que ahora viven en tablas
     separadas sin `unlock_factor_id`. Cuando se les añada esa columna,
     el resolver de Completionist solo necesita iterar sobre la nueva
     lista de modelos en `_COMPLETIONIST_MODELS`.

Toda operación es idempotente:
  - Si el achievement ya estaba desbloqueado, se devuelve un resultado
    con `achievement_was_already_unlocked=True` sin recalcular cascadas.
  - Los UserUnlock y UserStickerApplication ya existentes no se duplican;
    se actualizan in-place solo si cambia el `highest_stake_order` a uno
    mayor (caso sticker) o el `unlocked` pasa de False a True.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from app.extensions import db
from app.models import (
    Achievement,
    Unlockable,
    UnlockableType,
    UserAchievement,
    UserStickerApplication,
    UserUnlock,
)
from app.models.enums import UnlockSource

# =============================================================================
# Resultado público
# =============================================================================


@dataclass
class UnlockAchievementResult:
    """Resumen de lo que ocurrió al desbloquear un achievement.

    Pensado para devolverse a la capa HTTP o al sync de Steam y poder
    reportar al usuario qué se ha desbloqueado en cascada.
    """

    achievement: Achievement
    achievement_was_already_unlocked: bool
    cascaded_unlockables: list[Unlockable] = field(default_factory=list)
    cascaded_sticker_applications: list[UserStickerApplication] = field(
        default_factory=list
    )
    notes: list[str] = field(default_factory=list)

    @property
    def total_items_cascaded(self) -> int:
        return len(self.cascaded_unlockables) + len(self.cascaded_sticker_applications)


# =============================================================================
# Registry de resolvers especiales
# =============================================================================


_SpecialResolver = Callable[..., None]
_special_resolvers: dict[str, _SpecialResolver] = {}


def _special_resolver(steam_api_name: str):
    """Decorator: registra una función como resolver especial.

    El resolver se invoca tras la cascada genérica y recibe los kwargs:
        user_id, result, source, when
    Debe mutar `result` añadiendo lo que haya desbloqueado y, opcionalmente,
    notas para diagnóstico.
    """

    def wrapper(fn: _SpecialResolver) -> _SpecialResolver:
        if steam_api_name in _special_resolvers:
            raise RuntimeError(f"Ya hay un resolver registrado para {steam_api_name!r}")
        _special_resolvers[steam_api_name] = fn
        return fn

    return wrapper


# =============================================================================
# API pública
# =============================================================================


def unlock_achievement_for_user(
    user_id: int,
    achievement_id: int,
    source: UnlockSource = UnlockSource.STEAM_SYNC,
    when: Optional[datetime] = None,
) -> UnlockAchievementResult:
    """Marca un achievement como desbloqueado para el usuario y propaga.

    Args:
        user_id: id del usuario.
        achievement_id: id del achievement a marcar.
        source: origen del desbloqueo (manual del usuario o sync de Steam).
        when: timestamp del desbloqueo. Si es None, usa now(UTC).

    Returns:
        UnlockAchievementResult con el achievement, flag de idempotencia y
        listas de items / stickers cascaded.

    Raises:
        ValueError si el achievement no existe.
    """
    when = when or datetime.now(timezone.utc)

    achievement = db.session.get(Achievement, achievement_id)
    if achievement is None:
        raise ValueError(f"Achievement id={achievement_id} no encontrado")

    return _unlock_achievement(achievement, user_id, source, when)


def unlock_achievement_by_code(
    user_id: int,
    steam_api_name: str,
    source: UnlockSource = UnlockSource.STEAM_SYNC,
    when: Optional[datetime] = None,
) -> UnlockAchievementResult:
    """Variante por steam_api_name — útil para el sync con Steam Web API,
    que devuelve los achievements por su `apiname` y no por id interno.
    """
    when = when or datetime.now(timezone.utc)

    achievement = (
        db.session.query(Achievement)
        .filter(Achievement.steam_api_name == steam_api_name)
        .one_or_none()
    )
    if achievement is None:
        raise ValueError(f"Achievement steam_api_name={steam_api_name!r} no encontrado")

    return _unlock_achievement(achievement, user_id, source, when)


# =============================================================================
# Lógica interna
# =============================================================================


def _unlock_achievement(
    achievement: Achievement,
    user_id: int,
    source: UnlockSource,
    when: datetime,
) -> UnlockAchievementResult:
    """Núcleo compartido por las dos variantes públicas.

    Marca el UserAchievement, dispara la cascada genérica por shared factor
    y, si hay un resolver especial registrado, lo ejecuta. Hace commit al
    final (atomicidad: o todo o nada).
    """
    user_achievement = (
        db.session.query(UserAchievement)
        .filter_by(user_id=user_id, achievement_id=achievement.id)
        .one_or_none()
    )

    if user_achievement is not None and user_achievement.unlocked:
        # Idempotencia estricta: si ya estaba desbloqueado, no recalculamos
        # las cascadas. Si la lógica de cascada cambia, se requiere un
        # re-sync explícito que pase por las funciones de rebuild.
        return UnlockAchievementResult(
            achievement=achievement,
            achievement_was_already_unlocked=True,
        )

    if user_achievement is None:
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            unlocked=True,
            unlocked_at=when,
            source=source,
        )
        db.session.add(user_achievement)
    else:
        user_achievement.unlocked = True
        user_achievement.unlocked_at = when
        user_achievement.source = source

    result = UnlockAchievementResult(
        achievement=achievement,
        achievement_was_already_unlocked=False,
    )

    # 1) Cascada genérica por shared unlock_factor
    if achievement.unlock_factor_id is not None:
        for item in _cascade_shared_factor(
            user_id=user_id,
            unlock_factor_id=achievement.unlock_factor_id,
            source=source,
            when=when,
        ):
            result.cascaded_unlockables.append(item)

    # 2) Resolver especial (si existe)
    resolver = _special_resolvers.get(achievement.steam_api_name)
    if resolver is not None:
        resolver(user_id=user_id, result=result, source=source, when=when)

    db.session.commit()
    return result


def _cascade_shared_factor(
    user_id: int,
    unlock_factor_id: int,
    source: UnlockSource,
    when: datetime,
) -> list[Unlockable]:
    """Desbloquea todos los unlockables que comparten el unlock_factor dado.

    Devuelve la lista de items que pasaron efectivamente de "no desbloqueado"
    a "desbloqueado" (excluye los que ya lo estaban).
    """
    shared_items = (
        db.session.query(Unlockable)
        .filter(Unlockable.unlock_factor_id == unlock_factor_id)
        .all()
    )
    newly_unlocked: list[Unlockable] = []
    for item in shared_items:
        if _ensure_user_unlock(user_id, item.id, source, when):
            newly_unlocked.append(item)
    return newly_unlocked


def _ensure_user_unlock(
    user_id: int,
    unlockable_id: int,
    source: UnlockSource,
    when: datetime,
) -> bool:
    """Crea o actualiza una fila user_unlocks marcándola como desbloqueada.

    Returns:
        True si la fila pasó de no-desbloqueada a desbloqueada (caso
        interesante para el reporte de cascada).
        False si ya estaba desbloqueada (no-op).
    """
    user_unlock = (
        db.session.query(UserUnlock)
        .filter_by(user_id=user_id, unlockable_id=unlockable_id)
        .one_or_none()
    )
    if user_unlock is None:
        user_unlock = UserUnlock(
            user_id=user_id,
            unlockable_id=unlockable_id,
            unlocked=True,
            unlocked_at=when,
            source=source,
        )
        db.session.add(user_unlock)
        return True

    if user_unlock.unlocked:
        return False

    user_unlock.unlocked = True
    user_unlock.unlocked_at = when
    user_unlock.source = source
    return True


def _ensure_sticker_application(
    user_id: int,
    unlockable: Unlockable,
    stake_order: int,
    source: UnlockSource,
    when: datetime,
) -> Optional[UserStickerApplication]:
    """Crea/actualiza UserStickerApplication para un joker o deck.

    Pasamos el objeto `unlockable` (no solo el id) para que el `@validates`
    del modelo dispare la validación de tipo (JOKER | DECK).

    Returns:
        La USA si fue creada o promovida a un stake_order mayor.
        None si ya estaba en >= stake_order (no-op).
    """
    user_sticker = (
        db.session.query(UserStickerApplication)
        .filter_by(user_id=user_id, unlockable_id=unlockable.id)
        .one_or_none()
    )
    if user_sticker is None:
        user_sticker = UserStickerApplication(
            user_id=user_id,
            unlockable=unlockable,  # vía relationship → dispara @validates
            highest_stake_order=stake_order,
            earned_at=when,
            source=source,
        )
        db.session.add(user_sticker)
        return user_sticker

    if user_sticker.highest_stake_order >= stake_order:
        return None

    user_sticker.highest_stake_order = stake_order
    user_sticker.earned_at = when
    user_sticker.source = source
    return user_sticker


# =============================================================================
# Resolvers especiales
# =============================================================================
# Lista de modelos cuya tabla almacena items "completionables". Hoy solo
# Unlockable (que cubre jokers, decks, vouchers, tarots, planets, spectrals,
# booster_packs y challenge_decks). Cuando se añada unlock_factor_id a
# Blind, Tag y CardModifier, basta con extender esta lista.
_COMPLETIONIST_MODELS = [Unlockable]


@_special_resolver("BAL_23")  # Rule Breaker
def _resolve_rule_breaker(
    user_id: int,
    result: UnlockAchievementResult,
    source: UnlockSource,
    when: datetime,
) -> None:
    """Rule Breaker: desbloquea TODOS los challenge decks.

    A diferencia del cascade genérico, no requiere que los challenge decks
    compartan unlock_factor con el achievement — simplemente todos los que
    existan en la tabla.
    """
    challenges = (
        db.session.query(Unlockable)
        .filter(Unlockable.type == UnlockableType.CHALLENGE_DECK)
        .all()
    )
    cascaded_count = 0
    for challenge in challenges:
        if _ensure_user_unlock(user_id, challenge.id, source, when):
            result.cascaded_unlockables.append(challenge)
            cascaded_count += 1
    result.notes.append(
        f"Rule Breaker → {cascaded_count}/{len(challenges)} challenge decks "
        f"desbloqueados (resto ya estaban)."
    )


@_special_resolver("BAL_29")  # Completionist
def _resolve_completionist(
    user_id: int,
    result: UnlockAchievementResult,
    source: UnlockSource,
    when: datetime,
) -> None:
    """Completionist: desbloquea TODOS los items con unlock_factor.

    "Descubrir el 100% de la colección" implica haber desbloqueado todo lo
    que tiene condición de desbloqueo. Los items sin unlock_factor (típica-
    mente rarities comunes que están unlocked de base) no se tocan.

    Itera sobre `_COMPLETIONIST_MODELS` para soportar futura extensión a
    blinds/tags/editions cuando se les añada el campo unlock_factor_id.
    """
    total_items = 0
    cascaded_count = 0
    for Model in _COMPLETIONIST_MODELS:
        items = db.session.query(Model).filter(Model.unlock_factor_id.isnot(None)).all()
        total_items += len(items)
        for item in items:
            if _ensure_user_unlock(user_id, item.id, source, when):
                result.cascaded_unlockables.append(item)
                cascaded_count += 1
    result.notes.append(
        f"Completionist → {cascaded_count}/{total_items} items con factor "
        f"desbloqueados (resto ya estaban)."
    )


@_special_resolver("BAL_30")  # Completionist+
def _resolve_completionist_plus(
    user_id: int,
    result: UnlockAchievementResult,
    source: UnlockSource,
    when: datetime,
) -> None:
    """Completionist+: aplica Gold Sticker (stake_order=8) a TODOS los decks.

    El achievement se obtiene al ganar con cada deck en Gold Stake, lo cual
    implica que el usuario tiene Gold Sticker en cada uno. Backfilleamos
    los registros que falten.
    """
    decks = (
        db.session.query(Unlockable)
        .filter(Unlockable.type == UnlockableType.DECK)
        .all()
    )
    cascaded_count = 0
    for deck in decks:
        usa = _ensure_sticker_application(
            user_id=user_id,
            unlockable=deck,
            stake_order=8,
            source=source,
            when=when,
        )
        if usa is not None:
            result.cascaded_sticker_applications.append(usa)
            cascaded_count += 1
    result.notes.append(
        f"Completionist+ → Gold Sticker aplicado/promovido en "
        f"{cascaded_count}/{len(decks)} decks."
    )


@_special_resolver("BAL_31")  # Completionist++
def _resolve_completionist_plus_plus(
    user_id: int,
    result: UnlockAchievementResult,
    source: UnlockSource,
    when: datetime,
) -> None:
    """Completionist++: aplica Gold Sticker a TODOS los jokers.

    Inferencia simétrica a Completionist+: el achievement requiere tener
    Gold Sticker en cada joker, así que si está unlocked podemos backfillear
    las USA que falten (típicamente útil para el sync de Steam, donde la
    granularidad de "qué stake batiste cada joker" no está disponible).
    """
    jokers = (
        db.session.query(Unlockable)
        .filter(Unlockable.type == UnlockableType.JOKER)
        .all()
    )
    cascaded_count = 0
    for joker in jokers:
        usa = _ensure_sticker_application(
            user_id=user_id,
            unlockable=joker,
            stake_order=8,
            source=source,
            when=when,
        )
        if usa is not None:
            result.cascaded_sticker_applications.append(usa)
            cascaded_count += 1
    result.notes.append(
        f"Completionist++ → Gold Sticker aplicado/promovido en "
        f"{cascaded_count}/{len(jokers)} jokers."
    )
