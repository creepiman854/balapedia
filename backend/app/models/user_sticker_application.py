"""Modelo SQLAlchemy para la tabla unificada user_sticker_applications.

Reemplaza a los modelos UserJokerSticker y UserDeckSticker. Una vez aplicada
la migración M1, elimina esos dos modelos y todas sus referencias en el
código y en app/models/__init__.py.

Ubicación: app/models/user_sticker_application.py
"""
from datetime import datetime, timezone

from sqlalchemy.orm import validates

from app.extensions import db
from app.models.enums import UnlockSource


class UserStickerApplication(db.Model):
    """Sticker STAKE aplicado por un usuario a un JOKER o DECK.

    El registro guarda el stake más alto al que el usuario ha derrotado el
    elemento. El sticker visible (White/Red/Green/.../Gold) se resuelve por
    JOIN con la tabla `stickers` usando `highest_stake_order` como clave
    natural (sticker_order 1..8 con sticker_type='STAKE').

    Los stickers IN_RUN (Eternal, Perishable, Rental) NO se persisten aquí
    porque son estado efímero de una partida individual, no progresión.

    El polimorfismo es implícito gracias a la herencia CTI de unlockables:
    `unlockable_id` apunta a la tabla padre y `unlockables.type` distingue
    JOKER vs DECK. La validación se hace a nivel de aplicación porque MySQL
    no soporta CHECK con subqueries cross-table.
    """

    __tablename__ = "user_sticker_applications"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    unlockable_id = db.Column(
        db.Integer,
        db.ForeignKey("unlockables.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    highest_stake_order = db.Column(db.SmallInteger, nullable=False)
    earned_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )
    source = db.Column(
        db.Enum(UnlockSource, name="unlock_source"),
        nullable=False,
        default=UnlockSource.MANUAL,
    )

    __table_args__ = (
        db.CheckConstraint(
            "highest_stake_order BETWEEN 1 AND 8",
            name="ck_user_sticker_applications_order_range",
        ),
    )

    # back_populates explícito (coherente con UserUnlock / UserAchievement).
    # Requiere que User y Unlockable declaren `sticker_applications`
    # con back_populates="user"/"unlockable" respectivamente.
    user = db.relationship("User", back_populates="sticker_applications")
    unlockable = db.relationship("Unlockable", back_populates="sticker_applications")

    ALLOWED_UNLOCKABLE_TYPES = {"JOKER", "DECK"}

    @validates("unlockable")
    def _validate_unlockable_type(self, key, value):
        """Defensa de aplicación: solo JOKER y DECK pueden recibir stickers."""
        if value is not None and value.type.name not in self.ALLOWED_UNLOCKABLE_TYPES:
            raise ValueError(
                f"UserStickerApplication solo acepta unlockables de tipo "
                f"{sorted(self.ALLOWED_UNLOCKABLE_TYPES)}, "
                f"recibido: {value.type.name!r}"
            )
        return value

    @property
    def is_gold(self) -> bool:
        """Devuelve True si el usuario tiene el Gold Sticker en este item."""
        return self.highest_stake_order == 8

    def __repr__(self) -> str:
        return (
            f"<UserStickerApplication user_id={self.user_id} "
            f"unlockable_id={self.unlockable_id} "
            f"stake={self.highest_stake_order}>"
        )