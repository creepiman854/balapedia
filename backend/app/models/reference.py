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

from app.models.enums import (
    BlindType,
    ModifierType,
    StickerType,
)


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


class Stake(db.Model):
    """Nivel de dificultad de Balatro.

    Existen 8 stakes (White, Red, Green, Black, Blue, Purple, Orange, Gold)
    de dificultad ascendente. Cada uno añade modificadores acumulativos sobre
    los anteriores (p.ej. Red elimina el reward del Small Blind, Green sube
    el score scaling, etc.). Los stakes se desbloquean **por deck**: para
    desbloquear el Red Stake para el Blue Deck, hay que ganar el White Stake
    con el Blue Deck primero.

    Algunos stakes (Red, Green, Black, Blue, Gold) desbloquean además una
    nueva baraja al ganar; se documenta en ``unlocks_deck_name`` como
    referencia textual (no FK estricta, igual que ``planet_card_name`` en
    PokerHand: mantenemos los dominios desacoplados).
    """

    __tablename__ = "stakes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    # Orden secuencial 1-8 (White=1, ..., Gold=8). Indica también orden de unlock.
    stake_order = db.Column(db.SmallInteger, unique=True, nullable=False, index=True)
    color = db.Column(db.String(20), nullable=False)  # White, Red, Green, etc.
    effect_description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    # Nombre del Deck que se desbloquea al completar este stake (NULL si no desbloquea ninguno).
    unlocks_deck_name = db.Column(db.String(50), nullable=True)
    wiki_url = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Stake id={self.id} order={self.stake_order} name={self.name!r}>"


class Blind(db.Model):
    """Encuentro de combate en un Ante. Existen tres categorías:

    - **Small Blind**: primer encuentro de cada Ante. Score multiplier base 1x.
      Es opcional (puede skipearse a cambio de un Tag).
    - **Big Blind**: segundo encuentro de cada Ante. Score multiplier 1.5x.
      También skipeable por Tag.
    - **Boss Blind**: tercer encuentro, no skipeable. Tiene efectos especiales
      (la variedad real está aquí; ~30 boss blinds distintos). Score 2x.

    Algunos Boss Blinds son **Finisher Blinds**: aparecen solo a partir del
    Ante 8. En el wikitexto se marcan con ``ante = 8``; los normales con
    ``ante = Any``. Mantenemos el campo como string para preservar este
    matiz semántico.
    """

    __tablename__ = "blinds"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    blind_type = db.Column(
        db.Enum(BlindType, name="blind_type"),
        nullable=False,
        index=True,
    )
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    # Ante donde puede aparecer: "Any" (cualquiera) o un número como string ("8" para finishers).
    ante = db.Column(db.String(20), nullable=True)
    # Multiplicador de chips requeridos vs el ante base. Algunos boss blinds
    # tienen multiplicadores decimales (0.5, 1.5), de ahí el Float.
    score_multiplier = db.Column(db.Float, nullable=True)
    reward_money = db.Column(db.SmallInteger, nullable=True)
    # Compatibilidad con el Joker "Matador": algunos boss blinds son inmunes
    # a sus efectos. Se conserva como dato curioso para la UI.
    matador_compatible = db.Column(db.Boolean, nullable=False, default=True)
    wiki_url = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Blind id={self.id} type={self.blind_type.value} " f"name={self.name!r}>"
        )


class Tag(db.Model):
    """Recompensa que se obtiene al skipear un Small o Big Blind.

    Existen 24 Tags en el juego, cada uno con un efecto distinto que se
    dispara en condiciones variables (al entrar al shop, en la siguiente
    blind, inmediatamente, etc.). Algunos requieren descubrir un Joker o
    una edición primero para empezar a aparecer (campo ``unlock_condition``).

    El campo ``ante`` documenta a partir de qué Ante puede aparecer este Tag:
    9 de los 24 tags (Negative, Standard, Meteor, Buffoon, Handy, Garbage,
    Ethereal, Top-up, Orbital) NO pueden aparecer en Ante 1, los otros 15 sí.
    """

    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    # "Any" o número de Ante mínimo donde puede aparecer.
    ante = db.Column(db.String(20), nullable=True)
    # Condición de desbloqueo si la hay (p.ej. "Discover the Foil edition").
    # NULL para tags sin requisito.
    unlock_condition = db.Column(db.String(500), nullable=True)
    wiki_url = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name!r}>"


class CardModifier(db.Model):
    """Modificador de carta de Balatro (Enhancement / Edition / Seal).

    Los tres tipos comparten plantilla `{{Modifier info}}` en la wiki y la
    misma estructura de datos (nombre, descripción del efecto, imagen),
    por lo que se unifican en una sola tabla discriminada por
    ``modifier_type`` (análogo a cómo Tarots/Planets/Spectrals comparten
    la tabla ``consumables``).

    Total esperado en Balatro 1.0.0n: ~17 modificadores
    (8 Enhancements + 5 Editions + 4 Seals).
    """

    __tablename__ = "card_modifiers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    modifier_type = db.Column(
        db.Enum(ModifierType, name="modifier_type"),
        nullable=False,
        index=True,
    )
    effect = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    wiki_url = db.Column(db.String(500), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<CardModifier id={self.id} type={self.modifier_type.value} "
            f"name={self.name!r}>"
        )

class Sticker(db.Model):
    """Sticker aplicable a Jokers o Decks en Balatro.

    11 stickers en total:
      - 3 In-Run: Eternal, Perishable, Rental (efectos mecánicos durante
        partida; el jugador no los "desbloquea").
      - 8 Stake: White, Red, Green, Black, Blue, Purple, Orange, Gold
        (marcadores permanentes que indican haber ganado un Stake con
        ese Joker/Deck concreto). Los 8 corresponden 1:1 con los 8
        Stakes existentes; se enlazan vía ``stake_id``.

    El campo ``sticker_order`` da orden canónico de presentación dentro
    de cada tipo (1-3 para In-Run, 1-8 para Stake), no es único global.
    """

    __tablename__ = "stickers"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sticker_type = db.Column(
        db.Enum(StickerType, name="sticker_type"),
        nullable=False,
        index=True,
    )
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    # Para Stake Stickers: enlace al Stake correspondiente (1:1).
    # NULL para In-Run Stickers.
    stake_id = db.Column(
        db.Integer,
        db.ForeignKey("stakes.id"),
        nullable=True,
    )
    sticker_order = db.Column(db.SmallInteger, nullable=False, index=True)
    wiki_url = db.Column(db.String(500), nullable=True)

    stake = db.relationship("Stake")

    def __repr__(self) -> str:
        return (
            f"<Sticker id={self.id} type={self.sticker_type.value} "
            f"name={self.name!r}>"
        )
