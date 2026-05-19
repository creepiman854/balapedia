"""Schemas marshmallow para serializar entidades del catálogo a JSON.

Cada entidad expone un schema que define:
  - Qué campos van al cliente (sin filtrar IDs internos de FK, timestamps
    administrativos, etc.).
  - Cómo se serializan los enums (siempre por su `.name` UPPERCASE,
    estable entre versiones y coherente con cómo MySQL los almacena en
    la columna ENUM).
  - Cómo se serializan las relaciones nested cuando aportan valor sin
    explotar el payload (ej. UnlockFactor en Achievement permite mostrar
    la condición humana sin un round-trip extra).

Para las subclases CTI de Unlockable (Joker, Deck, etc.), los schemas
asumen que se les pasa una instancia de la SUBCLASE (no del padre):
`Joker.query.all()`, `Deck.query.all()`, etc. Los campos comunes del
padre se hacen pull-up via `attribute="unlockable.X"`.
"""

from __future__ import annotations

from marshmallow import Schema, fields

from app.models.enums import (
    BlindType,
    BoosterPackSize,
    BoosterPackType,
    JokerRarity,
    ModifierType,
    StickerType,
    UnlockableType,
    VoucherTier,
)

# =============================================================================
# Schemas compartidos / nested
# =============================================================================


class UnlockFactorSchema(Schema):
    """Catálogo de condiciones de desbloqueo compartidas.

    Se nesta en Achievement y en los subclasses de Unlockable que tienen
    `unlock_factor_id` enlazado, para que el frontend pueda mostrar la
    descripción humana en una sola llamada.
    """

    id = fields.Int()
    code = fields.Str()
    description = fields.Str()


class StakeSummarySchema(Schema):
    """Variante reducida de Stake para nestear dentro de Sticker.

    El sticker apunta a un Stake vía FK; exponer aquí el id + nombre +
    color basta para que el frontend renderice el badge sin otra query.
    """

    id = fields.Int()
    name = fields.Str()
    stake_order = fields.Int()
    color = fields.Str()


# =============================================================================
# Schemas de Unlockables (jerarquía CTI)
# =============================================================================
# Patrón común: cada subclase tiene sus propios campos + pull-up del padre
# Unlockable via `attribute="unlockable.X"`. Esto permite que el endpoint
# haga `Joker.query.all()` y pase el resultado directo al schema sin
# transformaciones manuales.


class JokerSchema(Schema):
    """Joker (subclase Unlockable). Campos propios + pull-up del padre."""

    id = fields.Int()

    # Campos propios de la tabla `jokers`
    rarity = fields.Enum(JokerRarity)
    effect_type = fields.Str(allow_none=True)
    activation = fields.Str(allow_none=True)
    buy_price = fields.Int(allow_none=True)
    sell_price = fields.Int(allow_none=True)
    in_shop = fields.Bool()
    has_negative_variant = fields.Bool()
    negative_image_url = fields.Str(allow_none=True)
    is_copyable = fields.Bool()
    is_perishable = fields.Bool()
    is_eternal = fields.Bool()

    # Pull-up del padre Unlockable
    type = fields.Enum(UnlockableType, attribute="unlockable.type")
    item_number = fields.Int(attribute="unlockable.item_number")
    name = fields.Str(attribute="unlockable.name")
    description = fields.Str(attribute="unlockable.description", allow_none=True)
    image_url = fields.Str(attribute="unlockable.image_url", allow_none=True)
    unlock_condition = fields.Str(
        attribute="unlockable.unlock_condition", allow_none=True
    )
    wiki_url = fields.Str(attribute="unlockable.wiki_url", allow_none=True)
    unlock_factor = fields.Nested(
        UnlockFactorSchema, attribute="unlockable.unlock_factor", allow_none=True
    )


class ConsumableSchema(Schema):
    """Consumable (Tarot, Planet o Spectral). Pull-up del padre Unlockable.

    El `type` del padre (TAROT / PLANET / SPECTRAL) discrimina entre los
    tres. El schema no diferencia: el endpoint filtra por tipo si es
    necesario.
    """

    id = fields.Int()

    # Campos propios
    buy_price = fields.Int(allow_none=True)
    sell_price = fields.Int(allow_none=True)
    in_shop = fields.Bool()

    # Pull-up del padre
    type = fields.Enum(UnlockableType, attribute="unlockable.type")
    item_number = fields.Int(attribute="unlockable.item_number")
    name = fields.Str(attribute="unlockable.name")
    description = fields.Str(attribute="unlockable.description", allow_none=True)
    image_url = fields.Str(attribute="unlockable.image_url", allow_none=True)
    unlock_condition = fields.Str(
        attribute="unlockable.unlock_condition", allow_none=True
    )
    wiki_url = fields.Str(attribute="unlockable.wiki_url", allow_none=True)
    unlock_factor = fields.Nested(
        UnlockFactorSchema, attribute="unlockable.unlock_factor", allow_none=True
    )


class DeckSchema(Schema):
    """Deck (subclase Unlockable). Sin campos propios — toda la info
    está en el padre."""

    id = fields.Int()

    type = fields.Enum(UnlockableType, attribute="unlockable.type")
    item_number = fields.Int(attribute="unlockable.item_number")
    name = fields.Str(attribute="unlockable.name")
    description = fields.Str(attribute="unlockable.description", allow_none=True)
    image_url = fields.Str(attribute="unlockable.image_url", allow_none=True)
    unlock_condition = fields.Str(
        attribute="unlockable.unlock_condition", allow_none=True
    )
    wiki_url = fields.Str(attribute="unlockable.wiki_url", allow_none=True)
    unlock_factor = fields.Nested(
        UnlockFactorSchema, attribute="unlockable.unlock_factor", allow_none=True
    )


class VoucherSchema(Schema):
    """Voucher (subclase Unlockable). Incluye tier y enlace al siguiente
    en la cadena Base→Upgraded."""

    id = fields.Int()

    voucher_tier = fields.Enum(VoucherTier)
    next_voucher_id = fields.Int(allow_none=True)

    type = fields.Enum(UnlockableType, attribute="unlockable.type")
    item_number = fields.Int(attribute="unlockable.item_number")
    name = fields.Str(attribute="unlockable.name")
    description = fields.Str(attribute="unlockable.description", allow_none=True)
    image_url = fields.Str(attribute="unlockable.image_url", allow_none=True)
    unlock_condition = fields.Str(
        attribute="unlockable.unlock_condition", allow_none=True
    )
    wiki_url = fields.Str(attribute="unlockable.wiki_url", allow_none=True)
    unlock_factor = fields.Nested(
        UnlockFactorSchema, attribute="unlockable.unlock_factor", allow_none=True
    )


class BoosterPackSchema(Schema):
    """Booster Pack (subclase Unlockable). Tipo de pack + tamaño + coste."""

    id = fields.Int()

    pack_type = fields.Enum(BoosterPackType)
    size = fields.Enum(BoosterPackSize)
    cost = fields.Int()

    type = fields.Enum(UnlockableType, attribute="unlockable.type")
    item_number = fields.Int(attribute="unlockable.item_number")
    name = fields.Str(attribute="unlockable.name")
    description = fields.Str(attribute="unlockable.description", allow_none=True)
    image_url = fields.Str(attribute="unlockable.image_url", allow_none=True)
    unlock_condition = fields.Str(
        attribute="unlockable.unlock_condition", allow_none=True
    )
    wiki_url = fields.Str(attribute="unlockable.wiki_url", allow_none=True)


class ChallengeDeckSchema(Schema):
    """Challenge Deck (subclase Unlockable). Modificadores + starter +
    banned + descripción de la baraja base."""

    id = fields.Int()

    modifier = fields.Str()
    starter = fields.Str(allow_none=True)
    banned = fields.Str(allow_none=True)
    deck_description = fields.Str(allow_none=True)

    type = fields.Enum(UnlockableType, attribute="unlockable.type")
    item_number = fields.Int(attribute="unlockable.item_number")
    name = fields.Str(attribute="unlockable.name")
    description = fields.Str(attribute="unlockable.description", allow_none=True)
    image_url = fields.Str(attribute="unlockable.image_url", allow_none=True)
    unlock_condition = fields.Str(
        attribute="unlockable.unlock_condition", allow_none=True
    )
    wiki_url = fields.Str(attribute="unlockable.wiki_url", allow_none=True)


# =============================================================================
# Schemas de reference data (tablas independientes)
# =============================================================================


class BlindSchema(Schema):
    """Blind: Small, Big o Boss. Sin jerarquía Unlockable."""

    id = fields.Int()
    name = fields.Str()
    blind_type = fields.Enum(BlindType)
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    ante = fields.Str(allow_none=True)
    score_multiplier = fields.Float()
    reward_money = fields.Int(allow_none=True)
    matador_compatible = fields.Bool()
    wiki_url = fields.Str(allow_none=True)


class TagSchema(Schema):
    """Tag (Boss Tag de Skip). Sin jerarquía Unlockable."""

    id = fields.Int()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    ante = fields.Str(allow_none=True)
    unlock_condition = fields.Str(allow_none=True)
    wiki_url = fields.Str(allow_none=True)


class CardModifierSchema(Schema):
    """Card Modifier: Enhancement, Edition o Seal."""

    id = fields.Int()
    name = fields.Str()
    modifier_type = fields.Enum(ModifierType)
    effect = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    wiki_url = fields.Str(allow_none=True)


class PokerHandSchema(Schema):
    """Poker Hand (jugada de poker reconocida por el juego)."""

    id = fields.Int()
    name = fields.Str()
    base_chips = fields.Int()
    base_mult = fields.Int()
    chips_per_level = fields.Int()
    mult_per_level = fields.Int()
    planet_card_name = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    hidden = fields.Bool()
    hand_order = fields.Int()
    wiki_url = fields.Str(allow_none=True)


class StakeSchema(Schema):
    """Stake (nivel de dificultad: White, Red, ..., Gold)."""

    id = fields.Int()
    name = fields.Str()
    stake_order = fields.Int()
    color = fields.Str()
    effect_description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    unlocks_deck_name = fields.Str(allow_none=True)
    wiki_url = fields.Str(allow_none=True)


class StickerSchema(Schema):
    """Sticker: In-Run (Eternal/Perishable/Rental) o Stake (W..Gold).

    Para los STAKE stickers se nesta el Stake correspondiente para que el
    cliente pueda renderizar badge + información sin otra query.
    """

    id = fields.Int()
    name = fields.Str()
    sticker_type = fields.Enum(StickerType)
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    sticker_order = fields.Int()
    wiki_url = fields.Str(allow_none=True)
    stake = fields.Nested(StakeSummarySchema, allow_none=True)


# =============================================================================
# Achievement
# =============================================================================


class AchievementSchema(Schema):
    """Achievement de Steam. Incluye el unlock_factor nested para que el
    frontend muestre la condición sin un round-trip extra."""

    id = fields.Int()
    steam_api_name = fields.Str()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    icon_url = fields.Str(allow_none=True)
    hidden = fields.Bool()
    unlock_factor = fields.Nested(UnlockFactorSchema, allow_none=True)
