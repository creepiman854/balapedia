"""Paquete de modelos. Reexporta todas las clases para registro en SQLAlchemy."""

from app.models.enums import (
    BlindType,
    BoosterPackSize,
    BoosterPackType,
    JokerRarity,
    ModifierType,
    UnlockSource,
    UnlockableType,
    VoucherTier,
)
from app.models.user import User
from app.models.unlockable import (
    BoosterPack,
    ChallengeDeck,
    Consumable,
    Deck,
    Joker,
    Unlockable,
    Voucher,
)
from app.models.achievement import Achievement
from app.models.progress import UserAchievement, UserUnlock
from app.models.reference import (
    Blind,
    CardModifier,
    PokerHand,
    Stake,
    Tag,
)

__all__ = [
    # Enums
    "BlindType",
    "BoosterPackSize",
    "BoosterPackType",
    "JokerRarity",
    "ModifierType",
    "UnlockSource",
    "UnlockableType",
    "VoucherTier",
    # Modelos
    "Achievement",
    "BoosterPack",
    "ChallengeDeck",
    "Consumable",
    "Deck",
    "Joker",
    "Unlockable",
    "User",
    "UserAchievement",
    "UserUnlock",
    "Voucher",
    # Modelos de datos de referencia
    "Blind",
    "CardModifier",
    "PokerHand",
    "Stake",
    "Tag",
]
