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
    """Tipo de Blind. Cuatro categorías en Balatro:

    - **Small**: primer encuentro de cada Ante. Skippable por Tag.
    - **Big**: segundo encuentro. Skippable por Tag.
    - **Boss**: tercer encuentro variable, con efectos especiales.
      Aparece en cualquier Ante (campo ``ante = Any``).
    - **Showdown**: boss blind exclusivo del Ante 8 (los 5 "finishers":
      Amber Acorn, Verdant Leaf, Violet Vessel, Crimson Heart, Cerulean
      Bell). En la wiki se cataloga en ``Category:Showdown Blinds``
      separadamente.
    """

    SMALL = "Small"
    BIG = "Big"
    BOSS = "Boss"
    SHOWDOWN = "Showdown"


class ModifierType(str, Enum):
    """Categoría de Card Modifier en Balatro.

    Los tres tipos se aplican a cartas pero con mecánicas distintas:
      - Enhancement: modifica la carta jugadora (chips, mult, dinero...).
      - Edition: efecto visual + scoring sobre cualquier carta (Joker,
        consumible, playing card).
      - Seal: marcador especial en una playing card con efecto al jugarla.
    """

    ENHANCEMENT = "Enhancement"
    EDITION = "Edition"
    SEAL = "Seal"


class StickerType(str, Enum):
    """Categoría de Sticker en Balatro.

    - IN_RUN: stickers con efecto mecánico durante la partida
      (Eternal, Perishable, Rental). Se aplican aleatoriamente a Jokers
      según el Stake en curso. No los desbloquea el usuario.
    - STAKE: marcadores de progreso permanente que aparecen en Jokers
      y Decks tras ganar un Stake específico con ellos. Los 8 stickers
      (White → Gold) corresponden 1:1 con los 8 Stakes.
    """

    IN_RUN = "InRun"
    STAKE = "Stake"
