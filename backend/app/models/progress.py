"""Tablas pivote: progreso del usuario sobre items y logros."""

from datetime import datetime, timezone

from app.extensions import db
from app.models.enums import UnlockSource


class UserUnlock(db.Model):
    """Progreso de un usuario sobre un item desbloqueable concreto.

    Cada registro indica que el usuario `user_id` ha (o no) desbloqueado
    el item `unlockable_id`. Marcamos también cuándo y por qué medio
    (manual o sincronización con Steam) para evitar conflictos en futuras
    sincronizaciones.
    """

    __tablename__ = "user_unlocks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unlockable_id = db.Column(
        db.Integer,
        db.ForeignKey("unlockables.id", ondelete="CASCADE"),
        nullable=False,
    )
    unlocked = db.Column(db.Boolean, nullable=False, default=False)
    unlocked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    source = db.Column(
        db.Enum(UnlockSource, name="unlock_source"),
        nullable=False,
        default=UnlockSource.MANUAL,
    )

    user = db.relationship("User", back_populates="unlocks")
    unlockable = db.relationship("Unlockable", back_populates="user_unlocks")

    __table_args__ = (
        # Cada par (usuario, item) aparece una sola vez: defensa en profundidad
        # contra duplicados a nivel de BD, además de la lógica de aplicación.
        db.UniqueConstraint(
            "user_id", "unlockable_id", name="uq_user_unlocks_user_item"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserUnlock user={self.user_id} item={self.unlockable_id} "
            f"unlocked={self.unlocked}>"
        )


class UserAchievement(db.Model):
    """Progreso de un usuario sobre un logro de Steam.

    Estructura paralela a UserUnlock pero apuntando a la tabla `achievements`.
    Usamos clave primaria compuesta (user_id, achievement_id) en lugar de
    una columna `id` extra porque la combinación es naturalmente única
    y nunca queremos múltiples registros del mismo logro para un usuario.
    """

    __tablename__ = "user_achievements"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    achievement_id = db.Column(
        db.Integer,
        db.ForeignKey("achievements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    unlocked = db.Column(db.Boolean, nullable=False, default=False)
    unlocked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    source = db.Column(
        db.Enum(UnlockSource, name="unlock_source"),
        nullable=False,
        default=UnlockSource.STEAM_SYNC,
    )

    user = db.relationship("User", back_populates="achievements")
    achievement = db.relationship("Achievement", back_populates="user_achievements")

    def __repr__(self) -> str:
        return (
            f"<UserAchievement user={self.user_id} ach={self.achievement_id} "
            f"unlocked={self.unlocked}>"
        )
