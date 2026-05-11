"""Enumerados centralizados para los modelos.

Encapsular los valores válidos en clases Enum aporta:
  - Tipado fuerte: el editor avisa si usamos un valor inválido.
  - Una única fuente de verdad: si añadimos un nuevo tipo, se cambia aquí.
  - Documentación implícita: el listado de valores es autodescriptivo.
"""

"""Enumerados centralizados para los modelos."""
from enum import Enum


class UnlockableType(str, Enum):
    """Categoría de cada elemento desbloqueable del juego."""

    JOKER = "joker"
    TAROT = "tarot"
    PLANET = "planet"
    SPECTRAL = "spectral"
    VOUCHER = "voucher"
    DECK = "deck"
    BOOSTER_PACK = "booster_pack"
    CHALLENGE_DECK = "challenge_deck"


class JokerRarity(str, Enum):
    """Rareza de un Joker."""

    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    LEGENDARY = "Legendary"


class VoucherTier(str, Enum):
    """Nivel de un Voucher dentro de su cadena de mejora."""

    BASE = "Base"
    UPGRADED = "Upgraded"


class UnlockSource(str, Enum):
    """Origen del registro de desbloqueo de un usuario."""

    MANUAL = "manual"
    STEAM_SYNC = "steam_sync"


class BoosterPackType(str, Enum):
    """Categoría de Booster Pack según el contenido que ofrece al abrirlo.

    Cada categoría aparece con tres tamaños distintos (Normal, Jumbo, Mega),
    formando un total de 15 booster packs distintos en el juego base.
    """

    ARCANA = "Arcana"  # contiene Tarot Cards
    CELESTIAL = "Celestial"  # contiene Planet Cards
    STANDARD = "Standard"  # contiene Playing Cards
    BUFFOON = "Buffoon"  # contiene Joker Cards
    SPECTRAL = "Spectral"  # contiene Spectral Cards


class BoosterPackSize(str, Enum):
    """Tamaño del Booster Pack, que determina precio y cantidad de opciones."""

    NORMAL = "Normal"  # más barato, menos cartas
    JUMBO = "Jumbo"  # intermedio
    MEGA = "Mega"  # más caro, permite elegir múltiples cartas


class BlindType(str, Enum):
    """Tipo de Blind: Small/Big (siempre presentes) o Boss (variable por Ante).

    Los Small y Big Blinds son fijos en cada Ante; los Boss Blinds varían
    y son los que aportan la dificultad real con sus efectos especiales.
    """

    SMALL = "Small"
    BIG = "Big"
    BOSS = "Boss"
