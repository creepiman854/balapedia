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


class UserJokerSticker(db.Model):
    """Stake Sticker más alto que el usuario tiene en cada Joker.

    Almacena solo el sticker más alto (no el historial) porque obtener
    un Stake Sticker desbloquea automáticamente todos los inferiores
    (regla del juego). Por ejemplo, si un usuario obtuvo Gold Sticker
    (orden 8) en el Joker base, implícitamente tiene todos los stickers
    1-8 sobre ese Joker.

    ``highest_stake_order`` referencia el ``stake_order`` del Stake
    correspondiente (1=White, 2=Red, ..., 8=Gold). Se valida con
    CheckConstraint para garantizar rango válido a nivel de BD.

    Clave primaria compuesta: solo puede existir una fila por
    (user, joker) — siempre la del sticker más alto.
    """

    __tablename__ = "user_joker_stickers"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # FK a unlockables.id donde type=JOKER. La integridad de tipo se
    # garantiza a nivel de aplicación, no de BD.
    joker_id = db.Column(
        db.Integer,
        db.ForeignKey("unlockables.id", ondelete="CASCADE"),
        primary_key=True,
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

    user = db.relationship("User", back_populates="joker_stickers")
    joker = db.relationship("Unlockable")

    __table_args__ = (
        db.CheckConstraint(
            "highest_stake_order BETWEEN 1 AND 8",
            name="ck_user_joker_stickers_order_range",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserJokerSticker user={self.user_id} joker={self.joker_id} "
            f"highest={self.highest_stake_order}>"
        )


class UserDeckSticker(db.Model):
    """Stake Sticker más alto que el usuario tiene en cada Deck.

    Estructura idéntica a UserJokerSticker pero apuntando a Decks
    en lugar de Jokers. Misma regla: solo se almacena el sticker más
    alto (los inferiores se infieren).
    """

    __tablename__ = "user_deck_stickers"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # FK a unlockables.id donde type=DECK.
    deck_id = db.Column(
        db.Integer,
        db.ForeignKey("unlockables.id", ondelete="CASCADE"),
        primary_key=True,
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

    user = db.relationship("User", back_populates="deck_stickers")
    deck = db.relationship("Unlockable")

    __table_args__ = (
        db.CheckConstraint(
            "highest_stake_order BETWEEN 1 AND 8",
            name="ck_user_deck_stickers_order_range",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<UserDeckSticker user={self.user_id} deck={self.deck_id} "
            f"highest={self.highest_stake_order}>"
        )
