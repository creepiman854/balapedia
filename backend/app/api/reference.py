"""Endpoints públicos del catálogo de reference data.

Cubre tablas independientes de la jerarquía Unlockable:
  - GET /api/blinds            + /api/blinds/<id>
  - GET /api/tags              + /api/tags/<id>
  - GET /api/card-modifiers    + /api/card-modifiers/<id>
  - GET /api/poker-hands       + /api/poker-hands/<id>
  - GET /api/stakes            + /api/stakes/<id>
  - GET /api/stickers          + /api/stickers/<id>

Cada endpoint LIST soporta paginación (?page=&per_page=), filtrado y
ordenamiento contra whitelist. Sin autenticación.

A diferencia de los unlockables (que usan joined inheritance), estas
tablas son flat — no requieren JOINs salvo el de Sticker→Stake (que se
maneja con joinedload para el nested del schema).
"""

from __future__ import annotations

from flask import Blueprint, jsonify
from sqlalchemy.orm import joinedload

from app.api._helpers import (
    apply_filters,
    apply_sort,
    paginate_query,
    parse_bool,
)
from app.api.schemas import (
    BlindSchema,
    CardModifierSchema,
    PokerHandSchema,
    StakeSchema,
    StickerSchema,
    TagSchema,
)
from app.extensions import db
from app.models import (
    Blind,
    BlindType,
    CardModifier,
    ModifierType,
    PokerHand,
    Stake,
    Sticker,
    StickerType,
    Tag,
)

reference_bp = Blueprint("catalog_reference", __name__, url_prefix="/api")


def _not_found(resource: str, resource_id: int):
    """Respuesta 404 consistente con el resto de la API."""
    return (
        jsonify(error="not_found", message=f"{resource} {resource_id} not found"),
        404,
    )


# =============================================================================
#  Blinds
# =============================================================================


_BLIND_FILTERS = {
    "blind_type": BlindType,
    "matador_compatible": parse_bool,
}

_BLIND_SORTS = {
    "name": Blind.name,
    "score_multiplier": Blind.score_multiplier,
    "blind_type": Blind.blind_type,
}


@reference_bp.route("/blinds", methods=["GET"])
def list_blinds():
    """Lista paginada de Blinds. Filtros por tipo (Small/Big/Boss) y
    compatibilidad con Matador."""
    query = Blind.query
    query = apply_filters(query, Blind, _BLIND_FILTERS)
    query = apply_sort(query, _BLIND_SORTS, default_sort="name")
    return jsonify(paginate_query(query, schema=BlindSchema()))


@reference_bp.route("/blinds/<int:blind_id>", methods=["GET"])
def get_blind(blind_id: int):
    """Detalle de un Blind por id."""
    blind = db.session.get(Blind, blind_id)
    if blind is None:
        return _not_found("Blind", blind_id)
    return jsonify(BlindSchema().dump(blind))


# =============================================================================
#  Tags
# =============================================================================


_TAG_SORTS = {
    "name": Tag.name,
}


@reference_bp.route("/tags", methods=["GET"])
def list_tags():
    """Lista paginada de Tags. Sin filtros (todos los tags son del mismo
    tipo conceptualmente)."""
    query = Tag.query
    query = apply_sort(query, _TAG_SORTS, default_sort="name")
    return jsonify(paginate_query(query, schema=TagSchema()))


@reference_bp.route("/tags/<int:tag_id>", methods=["GET"])
def get_tag(tag_id: int):
    """Detalle de un Tag por id."""
    tag = db.session.get(Tag, tag_id)
    if tag is None:
        return _not_found("Tag", tag_id)
    return jsonify(TagSchema().dump(tag))


# =============================================================================
#  Card Modifiers (Enhancements / Editions / Seals)
# =============================================================================


_CARD_MODIFIER_FILTERS = {
    "modifier_type": ModifierType,
}

_CARD_MODIFIER_SORTS = {
    "name": CardModifier.name,
    "modifier_type": CardModifier.modifier_type,
}


@reference_bp.route("/card-modifiers", methods=["GET"])
def list_card_modifiers():
    """Lista paginada de Card Modifiers. Filtro por tipo
    (Enhancement/Edition/Seal)."""
    query = CardModifier.query
    query = apply_filters(query, CardModifier, _CARD_MODIFIER_FILTERS)
    query = apply_sort(query, _CARD_MODIFIER_SORTS, default_sort="modifier_type")
    return jsonify(paginate_query(query, schema=CardModifierSchema()))


@reference_bp.route("/card-modifiers/<int:modifier_id>", methods=["GET"])
def get_card_modifier(modifier_id: int):
    """Detalle de un Card Modifier por id."""
    modifier = db.session.get(CardModifier, modifier_id)
    if modifier is None:
        return _not_found("CardModifier", modifier_id)
    return jsonify(CardModifierSchema().dump(modifier))


# =============================================================================
#  Poker Hands
# =============================================================================


_POKER_HAND_FILTERS = {
    "hidden": parse_bool,
}

_POKER_HAND_SORTS = {
    "hand_order": PokerHand.hand_order,
    "name": PokerHand.name,
    "base_chips": PokerHand.base_chips,
    "base_mult": PokerHand.base_mult,
}


@reference_bp.route("/poker-hands", methods=["GET"])
def list_poker_hands():
    """Lista paginada de Poker Hands. Filtro por hidden (Flush Five y
    otros escondidos requieren desbloqueo)."""
    query = PokerHand.query
    query = apply_filters(query, PokerHand, _POKER_HAND_FILTERS)
    query = apply_sort(query, _POKER_HAND_SORTS, default_sort="hand_order")
    return jsonify(paginate_query(query, schema=PokerHandSchema()))


@reference_bp.route("/poker-hands/<int:hand_id>", methods=["GET"])
def get_poker_hand(hand_id: int):
    """Detalle de un Poker Hand por id."""
    hand = db.session.get(PokerHand, hand_id)
    if hand is None:
        return _not_found("PokerHand", hand_id)
    return jsonify(PokerHandSchema().dump(hand))


# =============================================================================
#  Stakes
# =============================================================================


_STAKE_SORTS = {
    "stake_order": Stake.stake_order,
    "name": Stake.name,
}


@reference_bp.route("/stakes", methods=["GET"])
def list_stakes():
    """Lista paginada de Stakes (ordenados por stake_order por defecto)."""
    query = Stake.query
    query = apply_sort(query, _STAKE_SORTS, default_sort="stake_order")
    return jsonify(paginate_query(query, schema=StakeSchema()))


@reference_bp.route("/stakes/<int:stake_id>", methods=["GET"])
def get_stake(stake_id: int):
    """Detalle de un Stake por id."""
    stake = db.session.get(Stake, stake_id)
    if stake is None:
        return _not_found("Stake", stake_id)
    return jsonify(StakeSchema().dump(stake))


# =============================================================================
#  Stickers
# =============================================================================


_STICKER_FILTERS = {
    "sticker_type": StickerType,
}

_STICKER_SORTS = {
    "sticker_order": Sticker.sticker_order,
    "name": Sticker.name,
    "sticker_type": Sticker.sticker_type,
}


@reference_bp.route("/stickers", methods=["GET"])
def list_stickers():
    """Lista paginada de Stickers. Filtro por tipo (IN_RUN/STAKE).
    Eager-load del Stake nested para evitar N+1 en serialización."""
    query = Sticker.query.options(joinedload(Sticker.stake))
    query = apply_filters(query, Sticker, _STICKER_FILTERS)
    query = apply_sort(query, _STICKER_SORTS, default_sort="sticker_order")
    return jsonify(paginate_query(query, schema=StickerSchema()))


@reference_bp.route("/stickers/<int:sticker_id>", methods=["GET"])
def get_sticker(sticker_id: int):
    """Detalle de un Sticker por id."""
    sticker = db.session.get(Sticker, sticker_id)
    if sticker is None:
        return _not_found("Sticker", sticker_id)
    return jsonify(StickerSchema().dump(sticker))
