"""Modelos de datos de referencia del juego.

A diferencia de los Unlockables (items que el jugador desbloquea durante
la partida), los datos de referencia son información siempre disponible
sobre la mecánica del juego: tipos de Poker Hand, niveles de dificultad
(Stakes), Blinds, Tags y Card Modifiers.

Se modelan en tablas independientes (no bajo la jerarquía Unlockable)
porque conceptualmente son distintos: el usuario no los "desbloquea",
son referencia consultable en la app a modo de wiki integrada.
"""
from app.extensions import db


class PokerHand(db.Model):
    """Tipo de jugada de póker en Balatro.

    Cada jugada tiene un valor base (chips × mult) y se nivela mediante el
    Planet Card asociado, ganando chips_per_level y mult_per_level por cada
    uso de ese planet. No hay límite de nivel.

    Las jugadas "secretas" (``hidden=True``: Five of a Kind, Flush House,
    Flush Five) están ocultas hasta que el jugador las descubre por primera
    vez en una partida; siguen el mismo patrón de visibilidad que los
    achievements ocultos de Steam.

    El campo ``planet_card_name`` se almacena como VARCHAR (no FK a
    ``unlockables``) deliberadamente: mantiene los dos dominios desacoplados
    y evita acoplar la tabla ``poker_hands`` (datos de referencia) a la
    tabla ``unlockables`` (items desbloqueables). Si en el futuro se
    requirieran joins frecuentes, el JOIN por nombre sigue siendo posible.
    """
    __tablename__ = "poker_hands"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Scoring base al Nivel 1
    base_chips = db.Column(db.SmallInteger, nullable=False)
    base_mult = db.Column(db.SmallInteger, nullable=False)

    # Escalado por nivel (cada uso del planet card asociado suma esto)
    chips_per_level = db.Column(db.SmallInteger, nullable=False)
    mult_per_level = db.Column(db.SmallInteger, nullable=False)

    # Planet Card que sube esta hand de nivel. Nombre simple (no FK).
    planet_card_name = db.Column(db.String(50), nullable=True)

    # Descripción de cómo formar la jugada (extraída de "How to Play the Hand")
    description = db.Column(db.Text, nullable=True)

    # Las jugadas "secretas" (Five of a Kind, Flush House, Flush Five) están
    # ocultas hasta que el jugador las descubre.
    hidden = db.Column(db.Boolean, nullable=False, default=False)

    # Orden canónico para presentación en UI (1=High Card, 2=Pair, ...,
    # 9=Straight Flush, 10=Royal Flush, 11=Five of a Kind, etc.)
    hand_order = db.Column(db.SmallInteger, nullable=False, index=True)

    # URL pública en la wiki para enlace desde la app
    wiki_url = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<PokerHand id={self.id} name={self.name!r}>"