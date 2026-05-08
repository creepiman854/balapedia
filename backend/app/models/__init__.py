"""Paquete de modelos. Reexporta todas las clases para registro en SQLAlchemy."""
from app.models.enums import (
    UnlockableType,
    JokerRarity,
    VoucherTier,
    UnlockSource,
)
from app.models.user import User
from app.models.unlockable import (
    Unlockable,
    Joker,
    Consumable,
    Deck,
    Voucher,
)
from app.models.achievement import Achievement
from app.models.progress import UserUnlock, UserAchievement

__all__ = [
    # Enums
    "UnlockableType",
    "JokerRarity",
    "VoucherTier",
    "UnlockSource",
    # Modelos
    "User",
    "Unlockable",
    "Joker",
    "Consumable",
    "Deck",
    "Voucher",
    "Achievement",
    "UserUnlock",
    "UserAchievement",
]