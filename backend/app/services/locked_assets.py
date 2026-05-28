"""Catálogo de imágenes "locked" oficiales para los Unlockables.

Mapping estático de `UnlockableType` → URL de la wiki para los tres
subtipos que tienen un "card back" oficial cuando todavía no se han
descubierto:

    JOKER   → Locked_Joker.png
    VOUCHER → Locked_Voucher.png
    DECK    → Locked_Deck.png

Los demás subtipos (CONSUMABLE en sus tres variantes, BOOSTER_PACK,
CHALLENGE_DECK) están "available from start" en el juego base, no
exhiben dorso oficial en la colección, y por tanto no entran en este
mapping. Cuando esos casos aparezcan en mods o nuevas vistas con dorso,
basta con añadirlos aquí.

Diseño deliberado: NO se guarda en BD. Son URLs de la wiki oficial, no
cambian a menos que la wiki suba una nueva versión del PNG — escenario
que requiere intervención manual del mantenedor de todos modos. Tenerlo
en código permite:
  - Diff trazable en git si se actualiza alguna URL.
  - Importar el catálogo en tests sin tocar fixtures.
  - Resolver el URL para un item en O(1) sin round-trip a MySQL.

Si en el futuro hay variantes (e.g. "Locked Joker Negativo" para mods),
el shape se extiende sin romper este archivo: cambiamos los values a un
dict {variant: url} y el helper acepta un kwarg `variant`.

"""
from __future__ import annotations

from typing import Optional

from app.models import UnlockableType


# =============================================================================
# Catálogo
# =============================================================================
# URLs directas a los PNG (sin querystrings de cache-busting de MediaWiki).
# Tamaños de referencia (consistencia visual con el resto del grid):
#   Locked_Joker.png   138 x 188
#   Locked_Voucher.png 126 x 186
#   Locked_Deck.png    138 x 188
LOCKED_IMAGE_URLS: dict[UnlockableType, str] = {
    UnlockableType.JOKER: "https://balatrowiki.org/images/Locked_Joker.png",
    UnlockableType.VOUCHER: "https://balatrowiki.org/images/Locked_Voucher.png",
    UnlockableType.DECK: "https://balatrowiki.org/images/Locked_Deck.png",
}


# =============================================================================
# Helper público
# =============================================================================


def get_locked_image_url(unlockable_type: UnlockableType) -> Optional[str]:
    """Devuelve la URL del asset "locked" para el tipo dado.

    Args:
        unlockable_type: miembro del enum `UnlockableType`.

    Returns:
        URL del PNG correspondiente, o `None` si el tipo no tiene asset
        locked en el catálogo (CONSUMABLE, BOOSTER_PACK, CHALLENGE_DECK).

    Ejemplo:
        >>> get_locked_image_url(UnlockableType.JOKER)
        'https://balatrowiki.org/images/Locked_Joker.png'
        >>> get_locked_image_url(UnlockableType.TAROT) is None
        True
    """
    return LOCKED_IMAGE_URLS.get(unlockable_type)