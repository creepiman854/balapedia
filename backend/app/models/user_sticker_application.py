"""Modelo SQLAlchemy para la tabla unificada user_sticker_applications."""
from datetime import datetime, timezone
from sqlalchemy.orm import validates
from app.extensions import db


class UserStickerApplication(db.Model):
    """Sticker STAKE aplicado por un usuario a un JOKER o DECK.

    Implementa "Dual-Source Tracking": separamos el nivel alcanzado
    manualmente del alcanzado vía Steam. Así, al desvincular Steam,
    simplemente reseteamos el 'steam_stake_order' a 0 y el usuario
    recupera intacto su progreso manual.
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

    # Dual-source tracking
    manual_stake_order = db.Column(db.SmallInteger, nullable=False, default=0)
    steam_stake_order = db.Column(db.SmallInteger, nullable=False, default=0)

    earned_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.CheckConstraint(
            "manual_stake_order BETWEEN 0 AND 8",
            name="ck_usa_manual_order",
        ),
        db.CheckConstraint(
            "steam_stake_order BETWEEN 0 AND 8",
            name="ck_usa_steam_order",
        ),
    )

    user = db.relationship("User", back_populates="sticker_applications")
    unlockable = db.relationship("Unlockable", back_populates="sticker_applications")

    ALLOWED_UNLOCKABLE_TYPES = {"JOKER", "DECK", "CHALLENGE_DECK"}

    @validates("unlockable")
    def _validate_unlockable_type(self, key, value):
        if value is not None and value.type.name not in self.ALLOWED_UNLOCKABLE_TYPES:
            raise ValueError(
                f"UserStickerApplication solo acepta {self.ALLOWED_UNLOCKABLE_TYPES}"
            )
        return value

    @property
    def highest_stake_order(self) -> int:
        """Devuelve el stake efectivo más alto (el mayor entre manual y steam)."""
        return max(self.manual_stake_order, self.steam_stake_order)

    @property
    def is_gold(self) -> bool:
        return self.highest_stake_order == 8

    def __repr__(self) -> str:
        return (
            f"<UserStickerApplication user={self.user_id} item={self.unlockable_id} "
            f"manual={self.manual_stake_order} steam={self.steam_stake_order}>"
        )
