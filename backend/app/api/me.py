"""Endpoints autenticados de progreso del usuario.

Cubre las vistas que el frontend necesita para mostrar al usuario su
estado de avance en el juego:

  - GET /api/me/summary           -> stats agregados (dashboard / profile)
  - GET /api/me/jokers            -> catálogo + overlay de progreso por joker
  - GET /api/me/decks             -> catálogo + overlay (sticker dorado)
  - GET /api/me/vouchers          -> catálogo + overlay
  - GET /api/me/booster-packs     -> catálogo + overlay (forward-compat)
  - GET /api/me/challenge-decks   -> catálogo + overlay (cascade Rule Breaker)
  - GET /api/me/achievements      -> catálogo + overlay (unlocked + timestamp)

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

from flask import Blueprint, g, jsonify, request
from marshmallow import ValidationError
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
    BoosterPackSchema,
    ChallengeDeckSchema,
    DeckSchema,
    JokerSchema,
    VoucherSchema,
)
from app.extensions import db
from app.models import (
    Achievement,
    BoosterPack,
    ChallengeDeck,
    Deck,
    Joker,
    Unlockable,
    UnlockableType,
    UserAchievement,
    UserStickerApplication,
    UserUnlock,
    Voucher,
)
from app.models.enums import JokerRarity, UnlockSource
from app.services.achievements import unlock_achievement_for_user
from app.services.unlocks_service import set_unlock_for_user

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
        .outerjoin(
            UserUnlock,
            db.and_(
                UserUnlock.user_id == user.id, UserUnlock.unlockable_id == Unlockable.id
            ),
        )
        .filter(
            UserStickerApplication.user_id == user.id,
            db.or_(
                UserStickerApplication.manual_stake_order == 8,
                UserStickerApplication.steam_stake_order == 8,
            ),
            # Aseguramos que solo cuente los de ítems verdaderamente desbloqueados
            db.or_(
                UserUnlock.unlocked == True,
                Unlockable.unlock_condition.in_(
                    ["Available from start.", "Unlocked from start"]
                ),
            ),
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

    # Validamos si está disponible desde el principio o fue desbloqueado
    is_base_unlocked = item_dict.get("unlock_condition") in (
        "Available from start.",
        "Unlocked from start",
    )

    # EXCEPCIÓN FRONTEND-BACKEND: Los 5 primeros Challenge Decks son base_unlocked
    if item_dict.get("type") == "CHALLENGE_DECK":
        if str(item_dict.get("name", "")).upper() in [
            "THE OMELETTE",
            "15 MINUTE CITY",
            "RICH GET RICHER",
            "ON A KNIFE'S EDGE",
            "X-RAY VISION",
        ]:
            is_base_unlocked = True

    is_visually_unlocked = item_dict["unlocked_for_me"] or is_base_unlocked

    item_dict["highest_stake_order"] = (
        sticker.highest_stake_order if (sticker and is_visually_unlocked) else None
    )
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
# GET /api/me/vouchers
# =============================================================================


_VOUCHER_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
}


@me_progress_bp.route("/vouchers", methods=["GET"])
@require_auth
def list_my_vouchers():
    """Catálogo completo de vouchers + overlay de progreso del usuario.

    Endpoint hermano de `/api/me/decks` y `/api/me/jokers`. Existe
    porque sin él la cascade de unlock_factor compartido (e.g.
    BAL_07 Card Player → Nacho Tong, BAL_08 Card Discarder → Recyclomancy)
    NO es visible en el frontend: la cascade crea correctamente la fila
    UserUnlock para el voucher, pero CollectionView leía de
    `/api/vouchers` (público, sin overlay), así que nunca veía
    `unlocked_for_me=true`.

    Para mantener simetría con `list_my_decks`, también devuelve
    `highest_stake_order` por si en el futuro los vouchers acaban
    soportando stickers (hoy no, así que siempre será null). El coste
    de la query extra de stickers es despreciable y mantiene el
    contrato del overlay uniforme entre los tres endpoints.
    """
    user = g.user

    query = _build_unlockable_subclass_query(Voucher)
    query = apply_sort(query, _VOUCHER_SORTS, default_sort="item_number")
    paginated = paginate_query(query, schema=None)

    vouchers = paginated["items"]
    voucher_ids = [v.id for v in vouchers]
    unlocks_map, stickers_map = _fetch_user_progress_for_unlockables(
        user.id, voucher_ids
    )

    schema = VoucherSchema()
    items_data = [
        _overlay_unlockable_progress(
            schema.dump(voucher),
            unlocks_map.get(voucher.id),
            stickers_map.get(voucher.id),
        )
        for voucher in vouchers
    ]
    paginated["items"] = items_data
    return jsonify(paginated)


# =============================================================================
# GET /api/me/booster-packs
# =============================================================================


_BOOSTER_PACK_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
}


@me_progress_bp.route("/booster-packs", methods=["GET"])
@require_auth
def list_my_booster_packs():
    """Catálogo completo de booster packs + overlay de progreso del usuario.

    Cierra la simetría de los endpoints autenticados:
    `/api/me/jokers`, `/api/me/decks`, `/api/me/vouchers` y ahora también
    `/api/me/booster-packs`. Los cuatro subtipos de Unlockable que la
    vista de Colección renderiza tienen overlay uniforme.

    En vanilla Balatro los sobres son "available from start" (sin
    `unlock_factor_id`), así que la cascade no los afecta y este
    endpoint hoy devuelve `unlocked_for_me=false` para todos.

    Lo añadimos igualmente por dos razones:
      1. **Consistencia de API**: que el frontend pueda usar el mismo
         pattern de `{ authenticated }` para los cuatro subtipos y no
         haya excepciones que recordar.
      2. **Forward-compat para mods**: si en el futuro algún sobre
         comunitario (e.g. un "Spectral Pack" custom) tiene
         `unlock_factor_id` poblado, el endpoint ya está listo para
         exponer el overlay sin más cambios.
    """
    user = g.user

    query = _build_unlockable_subclass_query(BoosterPack)
    query = apply_sort(query, _BOOSTER_PACK_SORTS, default_sort="item_number")
    paginated = paginate_query(query, schema=None)

    packs = paginated["items"]
    pack_ids = [p.id for p in packs]
    unlocks_map, stickers_map = _fetch_user_progress_for_unlockables(user.id, pack_ids)

    schema = BoosterPackSchema()
    items_data = [
        _overlay_unlockable_progress(
            schema.dump(pack),
            unlocks_map.get(pack.id),
            stickers_map.get(pack.id),
        )
        for pack in packs
    ]
    paginated["items"] = items_data
    return jsonify(paginated)


# =============================================================================
# GET /api/me/challenge-decks
# =============================================================================


_CHALLENGE_DECK_SORTS = {
    "item_number": Unlockable.item_number,
    "name": Unlockable.name,
}


@me_progress_bp.route("/challenge-decks", methods=["GET"])
@require_auth
def list_my_challenge_decks():
    """Catálogo completo de Challenge Decks + overlay de progreso.

    Endpoint hermano de los demás `/api/me/<subtipo>`. Existe porque sin
    él la cascade de Rule Breaker (BAL_23) NO es visible en el frontend:
    la cascade crea correctamente las filas UserUnlock para los 20
    challenge decks pero CollectionView leería de `/api/challenge-decks`
    (público, sin overlay) y verían siempre `unlocked_for_me=false`
    aunque el usuario tenga el achievement completado.

    Los challenge decks soportarían `highest_stake_order` (son del
    namespace de Unlockable y su FK funciona) pero no se aplican stickers
    sobre ellos en el juego — el overlay seguirá devolviendo null para
    ese campo en todos los casos. Lo dejamos uniforme con el resto por
    consistencia del contrato.
    """
    user = g.user

    query = _build_unlockable_subclass_query(ChallengeDeck)
    query = apply_sort(query, _CHALLENGE_DECK_SORTS, default_sort="item_number")
    paginated = paginate_query(query, schema=None)

    challenges = paginated["items"]
    challenge_ids = [c.id for c in challenges]
    unlocks_map, stickers_map = _fetch_user_progress_for_unlockables(
        user.id, challenge_ids
    )

    schema = ChallengeDeckSchema()
    items_data = [
        _overlay_unlockable_progress(
            schema.dump(challenge),
            unlocks_map.get(challenge.id),
            stickers_map.get(challenge.id),
        )
        for challenge in challenges
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


# =============================================================================
# POST /api/me/unlocks
# =============================================================================


@me_progress_bp.route("/unlocks", methods=["POST"])
@require_auth
def set_my_unlock():
    """Marca un Unlockable como (des)bloqueado para el usuario actual.

    Body JSON:
      - `unlockable_id` (int, requerido): id de Joker / Consumable /
        Deck / Voucher / BoosterPack / ChallengeDeck. Los seis subtipos
        comparten id namespace en la tabla padre `unlockables`, así
        que un único endpoint cubre todos.
      - `unlocked` (bool, opcional, default `true`): nuevo estado. El
        botón del frontend manda siempre `true`; el flag explícito deja
        la puerta abierta a un futuro botón "desmarcar" sin tener que
        evolucionar el contrato del API.

    Respuestas:
      - **200**: `{ ok, unlocked_for_me, unlocked_at }`. Éxito —
        incluyendo el re-mark idempotente (re-aplicar el mismo estado
        responde 200 sin tocar la BD; preserva `unlocked_at`).
      - **400**: payload inválido (`unlockable_id` ausente / no
        entero, `unlocked` no booleano).
      - **401**: sin token o token inválido (`@require_auth`).
      - **404**: `unlockable_id` no existe en BD.

    El upsert vive en `app.services.unlocks_service.set_unlock_for_user`
    para que el futuro Steam-sync llame a la misma función con
    `source=UnlockSource.STEAM_SYNC` — un único punto de entrada al
    lifecycle de `UserUnlock` garantiza consistencia.
    """
    payload = request.get_json(silent=True) or {}

    # Validación inline: son solo 2 campos. Marshmallow sería overkill
    # y obligaría a definir un schema extra solo para este endpoint.
    # OJO: `isinstance(x, bool)` también devuelve True para bool subclase
    # de int en Python — descartamos bools explícitamente para que
    # `unlockable_id=True` no pase el check como si fuese 1.
    raw_id = payload.get("unlockable_id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, int):
        raise ValidationError({"unlockable_id": "required int (the Unlockable.id)"})

    raw_unlocked = payload.get("unlocked", True)
    if not isinstance(raw_unlocked, bool):
        raise ValidationError({"unlocked": "must be a boolean"})

    try:
        result = set_unlock_for_user(
            user_id=g.user.id,
            unlockable_id=raw_id,
            unlocked=raw_unlocked,
            source=UnlockSource.MANUAL,
        )
    except LookupError:
        # Traducimos LookupError → 404 con mensaje consistente con
        # el resto de la API (ver _not_found en unlockables.py).
        return (
            jsonify(
                error="not_found",
                message=f"Unlockable {raw_id} not found",
            ),
            404,
        )

    return jsonify(
        {
            "ok": True,
            "unlocked_for_me": result.user_unlock.unlocked,
            "unlocked_at": (
                result.user_unlock.unlocked_at.isoformat()
                if result.user_unlock.unlocked_at
                else None
            ),
        }
    )


# =============================================================================
# POST /api/me/achievements/unlock
# =============================================================================


@me_progress_bp.route("/achievements/unlock", methods=["POST"])
@require_auth
def set_my_achievement_unlock():
    """Marca un Achievement como desbloqueado para el usuario actual.

    Endpoint específico de achievements (no comparte path con
    `/api/me/unlocks` porque achievements NO son Unlockable: viven en
    una tabla flat propia con su pivot `user_achievements`).

    Body JSON:
      - `achievement_id` (int, requerido): id del Achievement.

    Respuestas:
      - **200**: `{ ok, unlocked_for_me, unlocked_at,
        was_already_unlocked }`. El `was_already_unlocked` deja al
        frontend distinguir cambio real de no-op idempotente (hoy no
        lo usa, pero deja la puerta abierta a feedback diferenciado
        sin tocar la API).
      - **400**: payload inválido (`achievement_id` ausente / no int).
      - **401**: sin token (`@require_auth`).
      - **404**: `achievement_id` no existe.

    Para cuentas con `steam_id` la sincronización de Steam es la
    fuente de verdad. El frontend lo enforza ocultando el botón en
    esas cuentas; deliberadamente NO bloqueamos a nivel de servidor
    para no cerrar la puerta a un futuro modo admin o un CLI de
    testing que necesite marcar manualmente.

    Delega en `services/achievements_service.unlock_achievement_for_user`
    con `source=UnlockSource.MANUAL` — la MISMA función que llama el
    sync de Steam con `source=UnlockSource.STEAM_SYNC`. Un único punto
    de entrada al lifecycle de `UserAchievement`, simétrico al de
    `set_unlock_for_user` para `UserUnlock`.

    """
    payload = request.get_json(silent=True) or {}

    raw_id = payload.get("achievement_id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, int):
        raise ValidationError({"achievement_id": "required int (the Achievement.id)"})

    raw_unlocked = payload.get("unlocked", True)
    if not isinstance(raw_unlocked, bool):
        raise ValidationError({"unlocked": "must be a boolean"})

    if not raw_unlocked:
        # Re-lock path
        from app.services.achievements import lock_achievement_for_user

        relock_result = lock_achievement_for_user(
            user_id=g.user.id,
            achievement_id=raw_id,
        )
        return jsonify(
            {
                "ok": True,
                "unlocked_for_me": False,
                "unlocked_at": None,
                **relock_result,
            }
        )

    try:
        result = unlock_achievement_for_user(
            user_id=g.user.id,
            achievement_id=raw_id,
            source=UnlockSource.MANUAL,
        )
    except ValueError as e:
        # Solo devolvemos 404 si el ValueError viene de que no existe el logro.
        # Si es un error de validación de SQLAlchemy, dejamos que explote con 500
        # para poder verlo en la terminal.
        if "no encontrado" in str(e) or "not found" in str(e):
            return (
                jsonify(
                    error="not_found",
                    message=f"Achievement {raw_id} not found",
                ),
                404,
            )
        raise e

    # Re-query del UserAchievement para devolver el `unlocked_at`
    # final. El service devuelve `UnlockAchievementResult` centrado en
    # el achievement + cascadas, no expone directamente la fila pivot
    # — esta query extra evita acoplar el shape del result a la
    # respuesta HTTP (si mañana el service añade más campos, este
    # endpoint sigue devolviendo solo lo que necesita el frontend).
    user_achievement = (
        db.session.query(UserAchievement)
        .filter_by(user_id=g.user.id, achievement_id=raw_id)
        .one_or_none()
    )

    return jsonify(
        {
            "ok": True,
            "unlocked_for_me": bool(user_achievement and user_achievement.unlocked),
            "unlocked_at": (
                user_achievement.unlocked_at.isoformat()
                if user_achievement and user_achievement.unlocked_at
                else None
            ),
            "was_already_unlocked": result.achievement_was_already_unlocked,
        }
    )


# =============================================================================
# POST /api/me/sticker-applications
# =============================================================================


@me_progress_bp.route("/sticker-applications", methods=["POST"])
@require_auth
def set_my_sticker_application():
    """Aplica o promociona un sticker (stake progression) a un Joker o Deck.

    Body JSON:
      - `unlockable_id` (int, requerido): id del Joker o Deck en la tabla
        `unlockables`. Los otros subtipos (Voucher, BoosterPack, etc.) no
        soportan stickers y se rechazan con 400.
      - `stake_order` (int 1-8, requerido): nivel del sticker a aplicar.
        1=White Stake, 2=Red, ..., 8=Gold. El endpoint SOLO promociona:
        si el usuario ya tiene un stake_order >= al solicitado, es no-op.

    Respuestas:
      - **200**: `{ ok, highest_stake_order }` — éxito (incluido no-op
        si el usuario ya tenía un stake_order mayor o igual).
      - **400**: payload inválido (unlockable_id/stake_order falta, fuera
        de rango 1-8, tipo de item no compatible con stickers).
      - **401**: sin token (@require_auth).
      - **404**: `unlockable_id` no existe.

    Política de promoción: solo sube, nunca baja. Si el usuario tiene
    stake_order=5 y envía 3, el response devuelve
    `highest_stake_order=5` sin cambio. Esto simplifica la UX del
    selector (el usuario no puede "desmarcarse" un sticker por error) y
    es consistente con cómo funciona el juego (los stickers son
    permanentes — una vez que ganas con un deck en Gold Stake, no
    puedes "des-ganar").

    Para cuentas Steam: la UI esconde el selector interactivo (solo
    read-only), pero NO bloqueamos a nivel de servidor para permitir
    un futuro modo admin o CLI de testing.
    """
    payload = request.get_json(silent=True) or {}

    # Validación: unlockable_id
    raw_id = payload.get("unlockable_id")
    if isinstance(raw_id, bool) or not isinstance(raw_id, int):
        raise ValidationError({"unlockable_id": "required int (the Unlockable.id)"})

    # Validación: stake_order (De 0 a 8 para permitir quitarlo)
    raw_stake = payload.get("stake_order")
    if not isinstance(raw_stake, int) or isinstance(raw_stake, bool):
        raise ValidationError({"stake_order": "required int (0-8)"})
    if raw_stake < 0 or raw_stake > 8:
        raise ValidationError({"stake_order": "must be between 0 and 8"})

    # Verificar que el unlockable existe...
    unlockable = db.session.get(Unlockable, raw_id)
    # ... código de validación de tipo JOKER / DECK ...

    if unlockable is None:
        return (
            jsonify(
                error="not_found",
                message=f"Unlockable {raw_id} not found",
            ),
            404,
        )

    # Solo Jokers y Decks soportan stickers (validación del modelo
    # UserStickerApplication dispara un error si el tipo es incorrecto,
    # pero atraparlo antes da un mensaje más claro al frontend).
    if unlockable.type not in (
        UnlockableType.JOKER,
        UnlockableType.DECK,
        UnlockableType.CHALLENGE_DECK,
    ):
        raise ValidationError(
            {
                "unlockable_id": (
                    f"Type {unlockable.type.name} does not support stickers. "
                    f"Only JOKER, DECK and CHALLENGE_DECK are valid."
                )
            }
        )

    # Upsert con política de "solo promover"
    user = g.user
    user_sticker = (
        db.session.query(UserStickerApplication)
        .filter_by(user_id=user.id, unlockable_id=raw_id)
        .one_or_none()
    )

    if user_sticker is None:
        if raw_stake > 0:  # Si manda 0 a un hueco vacío, es un no-op
            from datetime import datetime, timezone

            user_sticker = UserStickerApplication(
                user_id=user.id,
                unlockable_id=raw_id,
                manual_stake_order=raw_stake,
                earned_at=datetime.now(timezone.utc),
            )
            db.session.add(user_sticker)
    elif user_sticker.manual_stake_order != raw_stake:
        from datetime import datetime, timezone

        user_sticker.manual_stake_order = raw_stake
        user_sticker.earned_at = datetime.now(timezone.utc)

        # CLEANUP: Si tras el cambio ambos stakes quedan a 0, borramos la fila entera para no ensuciar la DB
        if user_sticker.manual_stake_order == 0 and user_sticker.steam_stake_order == 0:
            db.session.delete(user_sticker)
            user_sticker = None

    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "highest_stake_order": (
                user_sticker.highest_stake_order if user_sticker else None
            ),
        }
    )
