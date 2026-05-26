"""Servicio de UserUnlock.

Centraliza el upsert idempotente de la tabla `user_unlocks` para que
todos los caminos que (des)marquen un Unlockable para un usuario pasen
por la MISMA función:

  - POST /api/me/unlocks
        El botón "marcar como desbloqueado" del frontend
        (jokers/decks/vouchers/booster-packs/consumables/challenge-decks
        comparten el id namespace de la tabla padre `unlockables`).
  - Steam sync (rama futura)
        Cuando aterrice, leerá GetUserStats / GetPlayerAchievements y,
        por cada achievement que mapee 1:1 a un joker o deck (e.g.
        "win with Red Deck"), llamará a esta misma función pasando
        `source=UnlockSource.STEAM_SYNC`.

Mantener UN SOLO punto de entrada al lifecycle de UserUnlock evita la
clase de bugs por divergencia entre dos implementaciones del mismo
upsert — la misma lección que el fix de
`fix/api-consumables-type-filter` aplicada preventivamente.

Mismo patrón que `app/services/achievements_service.py`:
una función pura que toma user_id + unlockable_id + bandera + source,
hace el upsert con commit propio y devuelve un resultado estructurado.

## Idempotencia

Re-aplicar el mismo estado dos veces NO toca la fila (preserva el
`unlocked_at` original) y devuelve `changed=False`. El endpoint HTTP
lo traduce a 200 silencioso; un hipotético logger del sync de Steam
puede mirar `changed` para no spamear "X items synced" cuando en
realidad nada cambió.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.extensions import db
from app.models import Unlockable, UserUnlock
from app.models.enums import UnlockSource


@dataclass
class SetUnlockResult:
    """Resultado del upsert de `UserUnlock`.

    Attributes:
        user_unlock: la fila final (creada nueva o pre-existente).
        created: True si se insertó una fila nueva. False si ya
            existía (independientemente de si cambió o no su valor).
        changed: True si el campo `unlocked` ha cambiado de valor
            respecto al estado anterior, O si la fila se acaba de
            crear. False si el upsert no modificó nada (no-op).
    """

    user_unlock: UserUnlock
    created: bool
    changed: bool


def set_unlock_for_user(
    user_id: int,
    unlockable_id: int,
    unlocked: bool = True,
    source: UnlockSource = UnlockSource.MANUAL,
    when: Optional[datetime] = None,
) -> SetUnlockResult:
    """Marca un Unlockable como (des)bloqueado para un usuario.

    Args:
        user_id: id del usuario (sale de `g.user.id` en el endpoint).
        unlockable_id: id del Unlockable. Los seis subtipos (Joker,
            Consumable, Deck, Voucher, BoosterPack, ChallengeDeck)
            comparten el id namespace de la tabla padre.
        unlocked: nuevo estado. True = desbloqueado.
        source: origen del cambio. Por defecto MANUAL (botón del
            frontend). El Steam-sync pasará STEAM_SYNC.
        when: timestamp del cambio. Si es None usa `now(UTC)`. Se
            preserva el original en re-marks idempotentes.

    Returns:
        SetUnlockResult con la fila final + flags `created`/`changed`.

    Raises:
        LookupError: si el `unlockable_id` no existe. El endpoint lo
            traduce a HTTP 404; un sync probablemente lo loguea como
            warning y sigue con el siguiente item.

    ## Notas de diseño

    - **Pre-check del Unlockable**: validamos que existe ANTES de
      tocar `user_unlocks` para que un id inválido devuelva un 404
      limpio en vez de un IntegrityError de FK al commit.
    - **Re-mark idempotente preserva el `source`**: si el primer
      desbloqueo fue STEAM_SYNC y luego el usuario pulsa el botón
      MANUAL sobre algo ya desbloqueado, NO sobreescribimos el
      source — sería confuso ver "MANUAL" en una fila que en
      realidad vino de Steam. Si el estado cambia (de unlocked a
      locked o viceversa) sí actualizamos el `source` al nuevo
      origen, porque la fila representa una acción nueva.
    - **`unlocked_at` solo se setea cuando `unlocked` queda True**:
      crear una fila con `unlocked=False` deja `unlocked_at=None`
      (sería falso registrar un "timestamp de desbloqueo" para un
      no-desbloqueo).
    """
    when = when or datetime.now(timezone.utc)

    # Pre-check: traducimos id inexistente a una excepción tipada
    # ANTES de tocar `user_unlocks` para que el caller pueda mapearla
    # a 404 sin tener que parsear IntegrityErrors de FK.
    unlockable = db.session.get(Unlockable, unlockable_id)
    if unlockable is None:
        raise LookupError(f"Unlockable id={unlockable_id} not found")

    row = (
        db.session.query(UserUnlock)
        .filter_by(user_id=user_id, unlockable_id=unlockable_id)
        .one_or_none()
    )

    if row is None:
        row = UserUnlock(
            user_id=user_id,
            unlockable_id=unlockable_id,
            unlocked=unlocked,
            unlocked_at=when if unlocked else None,
            source=source,
        )
        db.session.add(row)
        db.session.commit()
        return SetUnlockResult(user_unlock=row, created=True, changed=True)

    # Ya existía. ¿Cambia el estado?
    if row.unlocked == unlocked:
        # No-op: preservamos `unlocked_at` y `source` tal cual estaban.
        return SetUnlockResult(user_unlock=row, created=False, changed=False)

    row.unlocked = unlocked
    row.unlocked_at = when if unlocked else None
    row.source = source
    db.session.commit()
    return SetUnlockResult(user_unlock=row, created=False, changed=True)
