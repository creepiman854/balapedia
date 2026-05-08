"""Enumerados centralizados para los modelos.

Encapsular los valores válidos en clases Enum aporta:
  - Tipado fuerte: el editor avisa si usamos un valor inválido.
  - Una única fuente de verdad: si añadimos un nuevo tipo, se cambia aquí.
  - Documentación implícita: el listado de valores es autodescriptivo.
"""
from enum import Enum


class UnlockableType(str, Enum):
    """Categoría de cada elemento desbloqueable del juego.

    Sirve como discriminador en la tabla `unlockables` para saber
    a qué tabla específica (jokers, consumables, decks, vouchers) pertenece.
    """
    JOKER = "joker"
    TAROT = "tarot"
    PLANET = "planet"
    SPECTRAL = "spectral"
    VOUCHER = "voucher"
    DECK = "deck"


class JokerRarity(str, Enum):
    """Rareza de un Joker, según definida en la wiki oficial de Balatro."""
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    LEGENDARY = "Legendary"


class VoucherTier(str, Enum):
    """Nivel de un Voucher dentro de su cadena de mejora.

    Los Vouchers en Balatro siempre vienen en pares: una versión Base
    y su Upgraded correspondiente, encadenadas por `next_voucher_id`.
    """
    BASE = "Base"
    UPGRADED = "Upgraded"


class UnlockSource(str, Enum):
    """Origen del registro de desbloqueo de un usuario.

    - MANUAL: el usuario marcó el item como desbloqueado en la web.
    - STEAM_SYNC: se importó automáticamente desde la API de Steam.

    La distinción permite no pisar las marcas manuales al sincronizar
    con Steam (el sync solo actualiza registros con source=STEAM_SYNC).
    """
    MANUAL = "manual"
    STEAM_SYNC = "steam_sync"