"""Paquete de modelos. Reexporta todas las clases para registro en SQLAlchemy."""

from app.models.enums import (
    BlindType,
    BoosterPackSize,
    BoosterPackType,
    JokerRarity,
    ModifierType,
    StickerType,
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
from app.models.progress import (
    UserAchievement,
    UserDeckSticker,
    UserJokerSticker,
    UserUnlock,
)
from app.models.reference import (
    Blind,
    CardModifier,
    PokerHand,
    Stake,
    Sticker,
    Tag,
)

__all__ = [
    # Enums
    "BlindType",
    "BoosterPackSize",
    "BoosterPackType",
    "JokerRarity",
    "ModifierType",
    "StickerType",
    "UnlockSource",
    "UnlockableType",
    "VoucherTier",
    # Modelos
    "Achievement",
    "Blind",
    "BoosterPack",
    "CardModifier",
    "ChallengeDeck",
    "Consumable",
    "Deck",
    "Joker",
    "PokerHand",
    "Stake",
    "Sticker",
    "Tag",
    "Unlockable",
    "User",
    "UserAchievement",
    "UserDeckSticker",
    "UserJokerSticker",
    "UserUnlock",
    "Voucher",
]
