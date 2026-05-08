"""Modelo Achievement: los 31 logros oficiales de Balatro en Steam."""
from app.extensions import db


class Achievement(db.Model):
    """Logro oficial del juego, sincronizable vía la Steam Web API.

    Se modela aparte de `Unlockable` porque conceptualmente es distinto:
    los unlockables son items del juego con propiedades funcionales
    (rareza, precio, efecto); los logros son metas externas con
    propiedades de meta (nombre interno de Steam, icono, oculto/visible).
    Mezclarlos forzaría columnas NULL y rompería la cohesión semántica.
    """
    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Nombre interno usado por la Steam API (p.ej. "ach_low_stakes_complete").
    # Es la clave estable para mapear lo que devuelve Steam a nuestro registro.
    steam_api_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_url = db.Column(db.String(500), nullable=True)
    # Logros ocultos: Steam no los muestra hasta desbloquearlos.
    hidden = db.Column(db.Boolean, nullable=False, default=False)

    user_achievements = db.relationship(
        "UserAchievement",
        back_populates="achievement",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Achievement id={self.id} name={self.name!r}>"