"""Endpoints autenticados de progreso del usuario.

Cubre las vistas que el frontend necesita para mostrar al usuario su
estado de avance en el juego:

  - GET /api/me/summary       -> stats agregados (dashboard / profile)
  - GET /api/me/jokers        -> catálogo + overlay de progreso por joker
  - GET /api/me/decks         -> catálogo + overlay (sticker dorado)
  - GET /api/me/achievements  -> catálogo + overlay (unlocked + timestamp)

Todos requieren autenticación Firebase (`@require_auth`) — el `user_id`
sale del token JWT, no de query params.

Patrón común para los endpoints de listado:
  1. Construir la query del catálogo (mismo helper que /api/<x>).
  2. Aplicar filtros, sort y paginación con los helpers genéricos.
  3. Recolectar los IDs de los items de la página actual.
  4. Cargar el progreso del usuario para esos IDs en 1-2 queries
     adicionales (evita N+1 sin recurrir a joins polimórficos complejos).
  5. Serializar con el schema base y mergear el overlay como dict.
"""

from __future__ import annotations

from typing import Optional

from flask import Blueprint, g, jsonify
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.api._helpers import (
    apply_filters,
    apply_sort,
    paginate_query,
    parse_bool,
)
from app.api.auth import require_auth
from app.api.schemas import (
    AchievementSchema,
    DeckSchema,
    JokerSchema,
)
from app.extensions import db
from app.models import (
    Achievement,
    Deck,
    Joker,
    Unlockable,
    UnlockableType,
    UserAchievement,
    UserStickerApplication,
    UserUnlock,
    Voucher,
)
from app.models.enums import JokerRarity

me_progress_bp = Blueprint("me_progress", __name__, url_prefix="/api/me")


# =============================================================================
# GET /api/me/summary
# =============================================================================


@me_progress_bp.route("/summary", methods=["GET"])
@require_auth
def get_summary():
    """Devuelve un resumen agregado del progreso del usuario.

    Pensado para dashboards y badges del perfil — una sola request da al
    frontend todo lo necesario para mostrar "X items desbloqueados", "Y%
    completado", "Gold Stickers conseguidos", "última sync con Steam".
    """
    user = g.user

    catalog_totals = dict(
        db.session.query(Unlockable.type, func.count(Unlockable.id))
        .group_by(Unlockable.type)
        .all()
    )

    user_unlocks_by_type = dict(
        db.session.query(Unlockable.type, func.count(UserUnlock.id))
        .join(UserUnlock, UserUnlock.unlockable_id == Unlockable.id)
        .filter(UserUnlock.user_id == user.id, UserUnlock.unlocked.is_(True))
        .group_by(Unlockable.type)
        .all()
    )

    by_type = {}
    for unlockable_type in UnlockableType:
        total = catalog_totals.get(unlockable_type, 0)
        unlocked = user_unlocks_by_type.get(unlockable_type, 0)
        percent = round(100.0 * unlocked / total, 1) if total else 0.0
        by_type[unlockable_type.name] = {
            "total": total,
            "unlocked": unlocked,
            "percent": percent,
        }

    achievements_total = Achievement.query.count()
    achievements_unlocked = UserAchievement.query.filter_by(
        user_id=user.id, unlocked=True
    ).count()
    achievements_percent = (
        round(100.0 * achievements_unlocked / achievements_total, 1)
        if achievements_total
        else 0.0
    )

    gold_query = (
        db.session.query(Unlockable.type, func.count(UserStickerApplication.user_id))
        .join(Unlockable, Unlockable.id == UserStickerApplication.unlockable_id)
        .filter(
            UserStickerApplication.user_id == user.id,
            UserStickerApplication.highest_stake_order == 8,
        )
        .group_by(Unlockable.type)
    )
    gold_by_type = dict(gold_query.all())
    gold_jokers = gold_by_type.get(UnlockableType.JOKER, 0)
    gold_decks = gold_by_type.get(UnlockableType.DECK, 0)

    return jsonify(
        {
            "user_id": user.id,
            "by_type": by_type,
            "achievements": {
                "total": achievements_total,
                "unlocked": achievements_unlocked,
                "percent": achievements_percent,
            },
            "gold_stickers": {
                "total": gold_jokers + gold_decks,
                "jokers": gold_jokers,
                "decks": gold_decks,
            },
            "last_steam_sync": (
                user.last_steam_sync.isoformat() if user.last_steam_sync else None
            ),
        }
    )


# =============================================================================
# Helpers de progress overlay
# =============================================================================


def _fetch_user_progress_for_unlockables(
    user_id: int, unlockable_ids: list[int]
) -> tuple[dict[int, UserUnlock], dict[int, UserStickerApplication]]:
    """Carga UserUnlock + UserStickerApplication para una lista de
    unlockable_ids del usuario, en 2 queries (evita N+1).

    Returns:
        (unlocks_map, stickers_map) — dicts indexados por unlockable_id.
        Las keys ausentes significan "el usuario no tiene unlock/sticker
        para ese item".
    """
    if not unlockable_ids:
        return {}, {}

    unlocks_map = {
        uu.unlockable_id: uu
        for uu in db.session.query(UserUnlock)
        .filter(
            UserUnlock.user_id == user_id,
            UserUnlock.unlockable_id.in_(unlockable_ids),
        )
        .all()
    }
    stickers_map = {
        usa.unlockable_id: usa
        for usa in db.session.query(UserStickerApplication)
        .filter(
            UserStickerApplication.user_id == user_id,
            UserStickerApplication.unlockable_id.in_(unlockable_ids),
        )
        .all()
    }
    return unlocks_map, stickers_map


def _fetch_user_progress_for_achievements(
    user_id: int, achievement_ids: list[int]
) -> dict[int, UserAchievement]:
    """Carga UserAchievement para una lista de achievement_ids del usuario,
    en 1 query."""
    if not achievement_ids:
        return {}
    return {
        ua.achievement_id: ua
        for ua in db.session.query(UserAchievement)
        .filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id.in_(achievement_ids),
        )
        .all()
    }


def _overlay_unlockable_progress(
    item_dict: dict,
    unlock: Optional[UserUnlock],
    sticker: Optional[UserStickerApplication],
) -> dict:
    """Mergea el progreso del usuario al dict serializado de un unlockable.

    Añade tres campos:
      - unlocked_for_me: bool
      - unlocked_at: ISO timestamp o None
      - highest_stake_order: int 1-8 o None (sticker dorado = 8)
    """
    item_dict["unlocked_for_me"] = bool(unlock and unlock.unlocked)
    item_dict["unlocked_at"] = (
        unlock.unlocked_at.isoformat() if unlock and unlock.unlocked_at else None
    )
    item_dict["highest_stake_order"] = sticker.highest_stake_order if sticker else None
    return item_dict


def _overlay_achievement_progress(
    item_dict: dict,
    user_achievement: Optional[UserAchievement],
) -> dict:
    """Mergea el progreso del usuario al dict serializado de un achievement.

    Añade dos campos:
      - unlocked_for_me: bool
      - unlocked_at: ISO timestamp o None
    """
    item_dict["unlocked_for_me"] = bool(user_achievement and user_achievement.unlocked)
    item_dict["unlocked_at"] = (
        user_achievement.unlocked_at.isoformat()
        if user_achievement and user_achievement.unlocked_at
        else None
    )
    return item_dict


def _build_unlockable_subclass_query(subclass_model):
    """Misma plantilla que en app/api/unlockables.py: JOIN explícito al
    padre + joinedload de unlock_factor para evitar N+1 al serializar.
    Duplicada localmente para no acoplar este módulo a uno privado."""
    return subclass_model.query.join(
        Unlockable, subclass_model.id == Unlockable.id
    ).options(
        joinedload(subclass_model.unlockable).joinedload(Unlockable.unlock_factor)
    )


# =============================================================================
# GET /api/me/jokers
# =============================================================================


_JOKER_FILTERS = {
    "rarity": JokerRarity,
    "in_shop": parse_bool,
    "has_negative_variant": parse_bool,
    "is_copyable": parse_bool,
    "is_perishable": parse_bool,
    "is_eternal": parse_bool,
}

_JOKER_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
    "rarity": Joker.rarity,
    "buy_price": Joker.buy_price,
}


@me_progress_bp.route("/jokers", methods=["GET"])
@require_auth
def list_my_jokers():
    """Catálogo completo de jokers + overlay de progreso del usuario.

    Cada item incluye los campos del catálogo público (mismo schema que
    /api/jokers) más tres campos extra:
      - unlocked_for_me, unlocked_at: de UserUnlock
      - highest_stake_order: de UserStickerApplication (None si no tiene)
    """
    user = g.user

    query = _build_unlockable_subclass_query(Joker)
    query = apply_filters(query, Joker, _JOKER_FILTERS)
    query = apply_sort(query, _JOKER_SORTS, default_sort="item_number")
    paginated = paginate_query(query, schema=None)

    jokers = paginated["items"]
    joker_ids = [j.id for j in jokers]
    unlocks_map, stickers_map = _fetch_user_progress_for_unlockables(user.id, joker_ids)

    schema = JokerSchema()
    items_data = [
        _overlay_unlockable_progress(
            schema.dump(joker),
            unlocks_map.get(joker.id),
            stickers_map.get(joker.id),
        )
        for joker in jokers
    ]
    paginated["items"] = items_data
    return jsonify(paginated)


# =============================================================================
# GET /api/me/decks
# =============================================================================


_DECK_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
}


@me_progress_bp.route("/decks", methods=["GET"])
@require_auth
def list_my_decks():
    """Catálogo completo de decks + overlay de progreso del usuario.

    Las decks también pueden recibir stickers (Gold Sticker vía
    Completionist+), por eso aplicamos el mismo overlay que para jokers.
    """
    user = g.user

    query = _build_unlockable_subclass_query(Deck)
    query = apply_sort(query, _DECK_SORTS, default_sort="item_number")
    paginated = paginate_query(query, schema=None)

    decks = paginated["items"]
    deck_ids = [d.id for d in decks]
    unlocks_map, stickers_map = _fetch_user_progress_for_unlockables(user.id, deck_ids)

    schema = DeckSchema()
    items_data = [
        _overlay_unlockable_progress(
            schema.dump(deck),
            unlocks_map.get(deck.id),
            stickers_map.get(deck.id),
        )
        for deck in decks
    ]
    paginated["items"] = items_data
    return jsonify(paginated)


# =============================================================================
# GET /api/me/achievements
# =============================================================================


_ACHIEVEMENT_FILTERS = {
    "hidden": parse_bool,
}

_ACHIEVEMENT_SORTS = {
    "id": Achievement.id,
    "steam_api_name": Achievement.steam_api_name,
    "name": Achievement.name,
}


@me_progress_bp.route("/achievements", methods=["GET"])
@require_auth
def list_my_achievements():
    """Catálogo completo de achievements + overlay de progreso del usuario.

    Cada item incluye los campos públicos (mismo schema que
    /api/achievements) más:
      - unlocked_for_me, unlocked_at: de UserAchievement
    """
    user = g.user

    query = Achievement.query.options(joinedload(Achievement.unlock_factor))
    query = apply_filters(query, Achievement, _ACHIEVEMENT_FILTERS)
    query = apply_sort(query, _ACHIEVEMENT_SORTS, default_sort="steam_api_name")
    paginated = paginate_query(query, schema=None)

    achievements = paginated["items"]
    achievement_ids = [a.id for a in achievements]
    user_achievements_map = _fetch_user_progress_for_achievements(
        user.id, achievement_ids
    )

    schema = AchievementSchema()
    items_data = [
        _overlay_achievement_progress(
            schema.dump(ach),
            user_achievements_map.get(ach.id),
        )
        for ach in achievements
    ]
    paginated["items"] = items_data
    return jsonify(paginated)
