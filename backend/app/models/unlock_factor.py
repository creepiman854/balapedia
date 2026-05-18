"""Modelo SQLAlchemy de la tabla unlock_factors."""

from app.extensions import db


class UnlockFactor(db.Model):
    """Catálogo normalizado de condiciones de desbloqueo.

    Cada factor representa una condición concreta que, al cumplirse,
    desbloquea uno o más items (unlockables) y/o uno o más achievements.
    La FK desde ambas tablas es nullable porque hay elementos sin
    condición compartida: jokers comunes desbloqueados de base, decks
    sin requisito, achievements puramente narrativos, etc.

    El campo `code` es un identificador estable y legible en
    SCREAMING_SNAKE_CASE (ej. 'REACH_ANTE_4', 'WIN_RUN',
    'DISCOVER_LEGENDARY_JOKER') que se usa programáticamente desde los
    seeds y los resolvers de auto-unlock. El campo `description` es el
    texto humano para mostrar en la UI.

    Ejemplo: el factor `REACH_ANTE_4` ("Reach Ante 4") es compartido
    por el achievement Ante Up! y el joker Showman; cuando un usuario
    cumple la condición, ambos se desbloquean en cascada vía el servicio
    de auto-unlock.
    """

    __tablename__ = "unlock_factors"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.String(500), nullable=False)

    # Items que comparten este factor. Típicamente cada item tiene su
    # propio factor único o lo comparte con UN achievement, pero la
    # cardinalidad es 1:N para soportar casos como "todas las cartas
    # planet descubiertas" → Astronomer joker (1 item, 1 achievement
    # apuntando al mismo factor).
    unlockables = db.relationship(
        "Unlockable",
        back_populates="unlock_factor",
        lazy="dynamic",
    )
    achievements = db.relationship(
        "Achievement",
        back_populates="unlock_factor",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<UnlockFactor code={self.code!r}>"
