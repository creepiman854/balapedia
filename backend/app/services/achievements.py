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

Ubicación: app/services/achievements.py
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

    ## Cascada en re-syncs (Mayo 2026)

    Antes hacíamos un atajo de "idempotencia estricta": si el achievement
    ya estaba desbloqueado, devolvíamos sin recalcular cascadas. Eso
    parecía sensato — ahorra trabajo en cada re-sync — pero rompe un
    escenario real:

      1. Usuario vincula Steam → sync inicial → marca BAL_07 (Card Player)
         como unlocked. Cascada corre y desbloquea Nacho Tong... IF Nacho
         Tong tiene unlock_factor_id apuntando a PLAY_2500_CARDS.
      2. Si en ese momento Nacho Tong NO tenía el factor (el backfill
         vino después, o el seed inicial tenía gap), la cascada NO lo
         pilla. El UserAchievement queda guardado pero el voucher se
         queda sin overlay.
      3. Días después corremos el backfill que enlaza Nacho Tong →
         PLAY_2500_CARDS.
      4. Usuario re-sincroniza Steam: BAL_07 ya estaba unlocked en BD →
         atajo de idempotencia estricta → cascada NO se ejecuta → Nacho
         Tong sigue locked.

    Solución: SIEMPRE correr la cascada y los resolvers, incluso cuando
    el achievement ya estaba desbloqueado. Es seguro porque las
    primitivas son idempotentes:

      - `_ensure_user_unlock` solo crea/promueve, nunca duplica.
      - `_ensure_sticker_application` solo promociona a stake_order mayor,
        nunca baja.

    El coste es N queries extra por sync (N = nº de achievements ya
    desbloqueados ≤ 31), que en SQLite de tests son ms y en MySQL real
    son irrelevantes. La ganancia es que cualquier mejora retrospectiva
    a los `unlock_factor` se aplica al siguiente sync sin intervención.

    El campo `achievement_was_already_unlocked` sigue siendo veraz —
    indica si EL ACHIEVEMENT cambió de estado, no si la cascada produjo
    cambios. Para esa información el caller mira las listas
    `cascaded_unlockables` / `cascaded_sticker_applications`.
    """
    user_achievement = (
        db.session.query(UserAchievement)
        .filter_by(user_id=user_id, achievement_id=achievement.id)
        .one_or_none()
    )

    achievement_was_already_unlocked = (
        user_achievement is not None and user_achievement.unlocked
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
    elif not user_achievement.unlocked:
        user_achievement.unlocked = True
        user_achievement.unlocked_at = when
        user_achievement.source = source
    # Si ya estaba unlocked NO sobreescribimos unlocked_at ni source —
    # preservamos el audit trail original (la primera vez que se
    # desbloqueó es la verdad histórica).

    result = UnlockAchievementResult(
        achievement=achievement,
        achievement_was_already_unlocked=achievement_was_already_unlocked,
    )

    # 1) Cascada genérica por shared unlock_factor — corre SIEMPRE,
    #    incluso si el achievement ya estaba unlocked, para pillar
    #    backfills retrospectivos de unlock_factor_id en Unlockables.
    if achievement.unlock_factor_id is not None:
        for item in _cascade_shared_factor(
            user_id=user_id,
            unlock_factor_id=achievement.unlock_factor_id,
            source=source,
            when=when,
        ):
            result.cascaded_unlockables.append(item)

    # 2) Resolver especial (si existe) — también corre SIEMPRE por la
    #    misma razón. Las primitivas son idempotentes, así que re-correr
    #    Completionist o Rule Breaker sobre un usuario que ya los tiene
    #    cascadeados es no-op.
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


# Busca _ensure_sticker_application y reemplázala por esta versión:
def _ensure_sticker_application(
    user_id: int,
    unlockable: Unlockable,
    stake_order: int,
    source: UnlockSource,
    when: datetime,
) -> Optional[UserStickerApplication]:
    user_sticker = (
        db.session.query(UserStickerApplication)
        .filter_by(user_id=user_id, unlockable_id=unlockable.id)
        .one_or_none()
    )
    if user_sticker is None:
        user_sticker = UserStickerApplication(
            user_id=user_id,
            unlockable=unlockable,
            earned_at=when,
        )
        if source == UnlockSource.MANUAL:
            user_sticker.manual_stake_order = stake_order
        else:
            user_sticker.steam_stake_order = stake_order
        db.session.add(user_sticker)
        return user_sticker

    changed = False
    # Evaluamos independientemente el canal Manual y el canal Steam
    if source == UnlockSource.MANUAL and user_sticker.manual_stake_order < stake_order:
        user_sticker.manual_stake_order = stake_order
        changed = True
    elif (
        source == UnlockSource.STEAM_SYNC
        and user_sticker.steam_stake_order < stake_order
    ):
        user_sticker.steam_stake_order = stake_order
        changed = True

    if changed:
        user_sticker.earned_at = when
        return user_sticker
    return None


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
    decks = (
        db.session.query(Unlockable)
        .filter(Unlockable.type == UnlockableType.DECK)
        .all()
    )
    cascaded_count = 0
    for deck in decks:
        # FIX: Asegurar primero el desbloqueo real de la carta
        if _ensure_user_unlock(user_id, deck.id, source, when):
            result.cascaded_unlockables.append(deck)

        usa = _ensure_sticker_application(user_id, deck, 8, source, when)
        if usa is not None:
            result.cascaded_sticker_applications.append(usa)
        cascaded_count += 1
    result.notes.append(
        f"Completionist+ → Desbloqueo y Gold Sticker en {cascaded_count}/{len(decks)} decks."
    )


@_special_resolver("BAL_31")  # Completionist++
def _resolve_completionist_plus_plus(
    user_id: int,
    result: UnlockAchievementResult,
    source: UnlockSource,
    when: datetime,
) -> None:
    jokers = (
        db.session.query(Unlockable)
        .filter(Unlockable.type == UnlockableType.JOKER)
        .all()
    )
    cascaded_count = 0
    for joker in jokers:
        # FIX: Asegurar primero el desbloqueo real de la carta
        if _ensure_user_unlock(user_id, joker.id, source, when):
            result.cascaded_unlockables.append(joker)

        usa = _ensure_sticker_application(user_id, joker, 8, source, when)
        if usa is not None:
            result.cascaded_sticker_applications.append(usa)
        cascaded_count += 1
    result.notes.append(
        f"Completionist++ → Desbloqueo y Gold Sticker en {cascaded_count}/{len(jokers)} jokers."
    )
