"""Endpoints públicos del catálogo de Unlockables.

Cubre las 6 subclases CTI:
  - GET /api/jokers           + /api/jokers/<id>
  - GET /api/consumables      + /api/consumables/<id>   (tarot/planet/spectral)
  - GET /api/decks            + /api/decks/<id>
  - GET /api/vouchers         + /api/vouchers/<id>
  - GET /api/booster-packs    + /api/booster-packs/<id>
  - GET /api/challenge-decks  + /api/challenge-decks/<id>

Cada endpoint LIST soporta paginación (?page=&per_page=), filtrado y
ordenamiento contra whitelist (ver app/api/_helpers.py). Sin autenticación
— son datos públicos del juego.

Patrón común para evitar N+1 al serializar:
  1. Query base sobre la subclase (`Joker.query`, etc.).
  2. JOIN explícito con `Unlockable` para permitir `ORDER BY` por columnas
     del padre (item_number, name).
  3. `joinedload` para eager-cargar las relaciones que el schema accede
     (`unlockable.X`, `unlockable.unlock_factor`).
"""
from __future__ import annotations

from flask import Blueprint, jsonify
from marshmallow import ValidationError
from sqlalchemy.orm import joinedload

from app.api._helpers import (
    apply_filters,
    apply_sort,
    paginate_query,
    parse_bool,
)
from app.api.schemas import (
    BoosterPackSchema,
    ChallengeDeckSchema,
    ConsumableSchema,
    DeckSchema,
    JokerSchema,
    VoucherSchema,
)
from app.extensions import db
from app.models import (
    BoosterPack,
    ChallengeDeck,
    Consumable,
    Deck,
    Joker,
    Unlockable,
    UnlockableType,
    Voucher,
    VoucherTier,
)
from app.models.enums import BoosterPackSize, BoosterPackType, JokerRarity


unlockables_bp = Blueprint("catalog_unlockables", __name__, url_prefix="/api")


# =============================================================================
#  Helpers locales
# =============================================================================


def _build_subclass_query(subclass_model):
    """Construye una query base para una subclase de Unlockable con
    el JOIN y joinedload necesarios para sort y serialización eficientes.
    """
    return (
        subclass_model.query
        .join(Unlockable, subclass_model.id == Unlockable.id)
        .options(
            joinedload(subclass_model.unlockable).joinedload(
                Unlockable.unlock_factor
            )
        )
    )


def _not_found(resource: str, resource_id: int):
    """Respuesta 404 consistente con el resto de la API."""
    return (
        jsonify(error="not_found", message=f"{resource} {resource_id} not found"),
        404,
    )


# =============================================================================
#  Jokers
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


@unlockables_bp.route("/jokers", methods=["GET"])
def list_jokers():
    """Lista paginada de Jokers con filtros y ordenamiento."""
    query = _build_subclass_query(Joker)
    query = apply_filters(query, Joker, _JOKER_FILTERS)
    query = apply_sort(query, _JOKER_SORTS, default_sort="item_number")
    return jsonify(paginate_query(query, schema=JokerSchema()))


@unlockables_bp.route("/jokers/<int:joker_id>", methods=["GET"])
def get_joker(joker_id: int):
    """Detalle de un Joker por id."""
    joker = db.session.get(Joker, joker_id)
    if joker is None:
        return _not_found("Joker", joker_id)
    return jsonify(JokerSchema().dump(joker))


# =============================================================================
#  Consumables (Tarot / Planet / Spectral comparten tabla)
# =============================================================================


_CONSUMABLE_FILTERS = {
    "in_shop": parse_bool,
}

_CONSUMABLE_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
    "buy_price": Consumable.buy_price,
}

_CONSUMABLE_VALID_TYPES = {
    UnlockableType.TAROT,
    UnlockableType.PLANET,
    UnlockableType.SPECTRAL,
}


def _resolve_enum(enum_cls, raw: str):
    """Resuelve un Enum a partir de un string probando primero por NAME
    y luego por VALUE.

    El resto de la API (apply_filters en _helpers.py) usa lookup por
    NAME, que coincide con la convención con la que marshmallow
    serializa los enums por defecto (fields.Enum → NAME en uppercase).
    El cliente recibe `"type": "TAROT"` y reenvía exactamente eso al
    filtrar, así que la NAME es la ruta natural.

    Soportamos VALUE como fallback por dos razones:
      1. Robustez: si en el futuro alguien cambia la convención de
         serialización del schema (e.g. by_value=True) o un cliente
         externo decide enviar el value directamente, el endpoint sigue
         funcionando sin romper a nadie.
      2. Diagnóstico: el bug original era exactamente lo contrario
         (lookup solo por VALUE, NAME no funcionaba) — aceptar ambos
         elimina la clase entera de bugs por desalineamiento de
         convenciones entre la capa de filtrado y la de serialización.

    Devuelve el miembro del enum o lanza KeyError si ningún lookup
    funciona. El caller decide cómo traducirlo a 400 (con o sin la
    whitelist de valores válidos en el mensaje).
    """
    # 1) NAME (UPPERCASE, convención del resto del API).
    try:
        return enum_cls[raw]
    except KeyError:
        pass
    # 2) VALUE (compatibilidad y robustez).
    try:
        return enum_cls(raw)
    except ValueError:
        raise KeyError(raw)


def _parse_consumable_type(raw: str) -> UnlockableType:
    """Acepta TAROT / PLANET / SPECTRAL para el filtro ?type=.

    Antes hacíamos `UnlockableType(raw)` (lookup por VALUE), inconsistente
    con `apply_filters` en `_helpers.py` que usa `Enum[raw]` (lookup por
    NAME). El frontend envía la NAME (que es lo que marshmallow le
    serializa de vuelta), así que el filtro estaba roto end-to-end y
    devolvía 400: invalid: 'TAROT'.

    El parser ahora delega en `_resolve_enum`, que prueba primero NAME
    (el camino natural) y cae a VALUE como fallback. Y si TODO falla, el
    400 incluye la lista de valores válidos para que cualquier futura
    discrepancia entre cliente y servidor se diagnostique en un solo
    refresh del navegador en vez de tener que adivinar.
    """
    try:
        value = _resolve_enum(UnlockableType, raw)
    except KeyError:
        valid_names = sorted(t.name for t in _CONSUMABLE_VALID_TYPES)
        raise ValidationError(
            {"type": f"invalid: {raw!r}; must be one of {valid_names}"}
        )
    if value not in _CONSUMABLE_VALID_TYPES:
        valid_names = sorted(t.name for t in _CONSUMABLE_VALID_TYPES)
        raise ValidationError(
            {"type": f"{raw!r} not allowed here; must be one of {valid_names}"}
        )
    return value


@unlockables_bp.route("/consumables", methods=["GET"])
def list_consumables():
    """Lista paginada de Consumables. Soporta ?type=TAROT|PLANET|SPECTRAL.

    El filtro `type` no usa apply_filters porque la columna vive en el
    padre Unlockable, no en la subclase.
    """
    query = _build_subclass_query(Consumable)

    from flask import request
    if "type" in request.args:
        type_enum = _parse_consumable_type(request.args["type"])
        query = query.filter(Unlockable.type == type_enum)

    query = apply_filters(query, Consumable, _CONSUMABLE_FILTERS)
    query = apply_sort(query, _CONSUMABLE_SORTS, default_sort="item_number")
    return jsonify(paginate_query(query, schema=ConsumableSchema()))


@unlockables_bp.route("/consumables/<int:consumable_id>", methods=["GET"])
def get_consumable(consumable_id: int):
    """Detalle de un Consumable por id."""
    consumable = db.session.get(Consumable, consumable_id)
    if consumable is None:
        return _not_found("Consumable", consumable_id)
    return jsonify(ConsumableSchema().dump(consumable))


# =============================================================================
#  Decks
# =============================================================================


_DECK_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
}


@unlockables_bp.route("/decks", methods=["GET"])
def list_decks():
    """Lista paginada de Decks. Sin filtros adicionales (todas las
    barajas son de un solo tipo)."""
    query = _build_subclass_query(Deck)
    query = apply_sort(query, _DECK_SORTS, default_sort="item_number")
    return jsonify(paginate_query(query, schema=DeckSchema()))


@unlockables_bp.route("/decks/<int:deck_id>", methods=["GET"])
def get_deck(deck_id: int):
    """Detalle de una Deck por id."""
    deck = db.session.get(Deck, deck_id)
    if deck is None:
        return _not_found("Deck", deck_id)
    return jsonify(DeckSchema().dump(deck))


# =============================================================================
#  Vouchers
# =============================================================================


_VOUCHER_FILTERS = {
    "voucher_tier": VoucherTier,
}

_VOUCHER_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
    "voucher_tier": Voucher.voucher_tier,
}


@unlockables_bp.route("/vouchers", methods=["GET"])
def list_vouchers():
    """Lista paginada de Vouchers. Filtro por tier (Base/Upgraded)."""
    query = _build_subclass_query(Voucher)
    query = apply_filters(query, Voucher, _VOUCHER_FILTERS)
    query = apply_sort(query, _VOUCHER_SORTS, default_sort="item_number")
    return jsonify(paginate_query(query, schema=VoucherSchema()))


@unlockables_bp.route("/vouchers/<int:voucher_id>", methods=["GET"])
def get_voucher(voucher_id: int):
    """Detalle de un Voucher por id."""
    voucher = db.session.get(Voucher, voucher_id)
    if voucher is None:
        return _not_found("Voucher", voucher_id)
    return jsonify(VoucherSchema().dump(voucher))


# =============================================================================
#  Booster Packs
# =============================================================================


_BOOSTER_PACK_FILTERS = {
    "pack_type": BoosterPackType,
    "size": BoosterPackSize,
}

_BOOSTER_PACK_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
    "cost": BoosterPack.cost,
}


@unlockables_bp.route("/booster-packs", methods=["GET"])
def list_booster_packs():
    """Lista paginada de Booster Packs. Filtros por tipo y tamaño."""
    query = _build_subclass_query(BoosterPack)
    query = apply_filters(query, BoosterPack, _BOOSTER_PACK_FILTERS)
    query = apply_sort(query, _BOOSTER_PACK_SORTS, default_sort="item_number")
    return jsonify(paginate_query(query, schema=BoosterPackSchema()))


@unlockables_bp.route("/booster-packs/<int:pack_id>", methods=["GET"])
def get_booster_pack(pack_id: int):
    """Detalle de un Booster Pack por id."""
    pack = db.session.get(BoosterPack, pack_id)
    if pack is None:
        return _not_found("BoosterPack", pack_id)
    return jsonify(BoosterPackSchema().dump(pack))


# =============================================================================
#  Challenge Decks
# =============================================================================


_CHALLENGE_DECK_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
}


@unlockables_bp.route("/challenge-decks", methods=["GET"])
def list_challenge_decks():
    """Lista paginada de Challenge Decks."""
    query = _build_subclass_query(ChallengeDeck)
    query = apply_sort(query, _CHALLENGE_DECK_SORTS, default_sort="item_number")
    return jsonify(paginate_query(query, schema=ChallengeDeckSchema()))


@unlockables_bp.route("/challenge-decks/<int:challenge_id>", methods=["GET"])
def get_challenge_deck(challenge_id: int):
    """Detalle de un Challenge Deck por id."""
    challenge = db.session.get(ChallengeDeck, challenge_id)
    if challenge is None:
        return _not_found("ChallengeDeck", challenge_id)
    return jsonify(ChallengeDeckSchema().dump(challenge))