"""Modelos de los items desbloqueables: padre Unlockable + tablas hijas específicas.

Patrón aplicado: Class Table Inheritance (herencia de tabla por clase),
también llamado "Joined Inheritance" en la literatura de ORMs.

  - `unlockables` contiene los campos comunes a todos los items.
  - `jokers`, `consumables`, `decks`, `vouchers` extienden con campos propios.
  - La relación es 1:1 entre `unlockables` y cada hija (mediada por `id` FK).
  - El campo `type` discrimina a qué hija pertenece cada registro.

Justificación: mantiene la integridad referencial (cada registro hijo apunta
a un padre real), permite consultas transversales eficientes desde el padre,
y evita columnas NULL masivas que tendría una tabla única.
"""

from app.extensions import db
from app.models.enums import (
    BoosterPackSize,
    BoosterPackType,
    JokerRarity,
    UnlockableType,
    VoucherTier,
)


class Unlockable(db.Model):
    """Tabla padre con los campos comunes a todos los items desbloqueables.

    Cualquier elemento del juego (joker, carta, vale, baraja) tiene un registro
    aquí. El campo `type` indica de qué tipo concreto es y por tanto en qué
    tabla hija viven sus datos específicos.
    """

    __tablename__ = "unlockables"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(
        db.Enum(UnlockableType, name="unlockable_type"),
        nullable=False,
        index=True,
    )
    # item_number: el "number" que viene de la wiki, único por tipo.
    # Sirve para ordenar la UI igual que el juego y para upsert idempotente.
    item_number = db.Column(db.SmallInteger, nullable=False)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    unlock_condition = db.Column(db.String(500), nullable=True)
    wiki_url = db.Column(db.String(500), nullable=True)

    # Relaciones 1:1 a las tablas hijas (una y solo una se rellena por registro,
    # según el valor de `type`).
    joker = db.relationship(
        "Joker",
        uselist=False,
        back_populates="unlockable",
        cascade="all, delete-orphan",
    )
    consumable = db.relationship(
        "Consumable",
        uselist=False,
        back_populates="unlockable",
        cascade="all, delete-orphan",
    )
    deck = db.relationship(
        "Deck",
        uselist=False,
        back_populates="unlockable",
        cascade="all, delete-orphan",
    )
    voucher = db.relationship(
        "Voucher",
        uselist=False,
        back_populates="unlockable",
        cascade="all, delete-orphan",
        foreign_keys="Voucher.id",  # disambigua de next_voucher_id
    )
    booster_pack = db.relationship(
        "BoosterPack",
        uselist=False,
        back_populates="unlockable",
        cascade="all, delete-orphan",
    )

    challenge_deck = db.relationship(
        "ChallengeDeck",
        uselist=False,
        back_populates="unlockable",
        cascade="all, delete-orphan",
    )

    # Relación inversa con la tabla pivote de progreso de usuarios
    user_unlocks = db.relationship(
        "UserUnlock",
        back_populates="unlockable",
        cascade="all, delete-orphan",
    )

    unlock_factor_id = db.Column(
        db.Integer,
        db.ForeignKey("unlock_factors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    unlock_factor = db.relationship("UnlockFactor", back_populates="unlockables")

    sticker_applications = db.relationship(
        "UserStickerApplication",
        back_populates="unlockable",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Garantiza que cada (tipo, número) sea único: permite upsert idempotente
        # desde el scraper sin riesgo de duplicar items al re-poblar la BD.
        db.UniqueConstraint("type", "item_number", name="uq_unlockables_type_number"),
    )

    def __repr__(self) -> str:
        return f"<Unlockable id={self.id} type={self.type.value} name={self.name!r}>"


class Joker(db.Model):
    """Datos específicos de los Jokers."""

    __tablename__ = "jokers"

    id = db.Column(db.Integer, db.ForeignKey("unlockables.id"), primary_key=True)

    rarity = db.Column(
        db.Enum(JokerRarity, name="joker_rarity"),
        nullable=False,
        index=True,
    )
    effect_type = db.Column(db.String(50), nullable=True, index=True)
    activation = db.Column(db.String(50), nullable=True)
    buy_price = db.Column(db.SmallInteger, nullable=True, index=True)
    sell_price = db.Column(db.SmallInteger, nullable=True)
    in_shop = db.Column(db.Boolean, nullable=False, default=True)
    has_negative_variant = db.Column(db.Boolean, nullable=False, default=False)
    negative_image_url = db.Column(db.String(500), nullable=True)
    is_copyable = db.Column(db.Boolean, nullable=False, default=False)
    is_perishable = db.Column(db.Boolean, nullable=False, default=False)
    is_eternal = db.Column(db.Boolean, nullable=False, default=False)

    unlockable = db.relationship("Unlockable", back_populates="joker")

    def __repr__(self) -> str:
        return f"<Joker id={self.id} rarity={self.rarity.value}>"


class Consumable(db.Model):
    """Datos específicos compartidos por Tarots, Planets y Spectrals.

    Los tres tipos comparten la misma plantilla `Consumable info` en la wiki
    y los mismos campos de dato (precio compra/venta, in_shop), por lo que
    una sola tabla los modela limpiamente. La distinción entre tarot/planet/
    spectral viene del campo `type` del padre `unlockables`.
    """

    __tablename__ = "consumables"

    id = db.Column(db.Integer, db.ForeignKey("unlockables.id"), primary_key=True)

    buy_price = db.Column(db.SmallInteger, nullable=True, index=True)
    sell_price = db.Column(db.SmallInteger, nullable=True)
    in_shop = db.Column(db.Boolean, nullable=False, default=True)

    unlockable = db.relationship("Unlockable", back_populates="consumable")

    def __repr__(self) -> str:
        return f"<Consumable id={self.id}>"


class Deck(db.Model):
    """Datos específicos de las Barajas.

    Casi toda la información de una baraja vive en el padre `Unlockable`
    (nombre, descripción, imagen, condición de desbloqueo). Esta tabla
    existe por simetría arquitectónica y para anclar el FK desde
    `user_unlocks` con tipado consistente; queda preparada por si en el
    futuro añadimos campos específicos.
    """

    __tablename__ = "decks"

    id = db.Column(db.Integer, db.ForeignKey("unlockables.id"), primary_key=True)

    unlockable = db.relationship("Unlockable", back_populates="deck")

    def __repr__(self) -> str:
        return f"<Deck id={self.id}>"


class Voucher(db.Model):
    """Datos específicos de los Vales (Vouchers).

    Modela la cadena Base -> Upgraded mediante una auto-referencia a
    `unlockables.id` en `next_voucher_id`. Los vales Upgraded tienen
    `next_voucher_id = NULL` (fin de cadena); los Base apuntan a su
    versión mejorada.
    """

    __tablename__ = "vouchers"

    id = db.Column(db.Integer, db.ForeignKey("unlockables.id"), primary_key=True)

    voucher_tier = db.Column(
        db.Enum(VoucherTier, name="voucher_tier"),
        nullable=False,
        index=True,
    )
    next_voucher_id = db.Column(
        db.Integer,
        db.ForeignKey("unlockables.id"),
        nullable=True,
    )

    unlockable = db.relationship(
        "Unlockable",
        back_populates="voucher",
        foreign_keys=[id],
    )
    next_voucher = db.relationship(
        "Unlockable",
        foreign_keys=[next_voucher_id],
    )

    def __repr__(self) -> str:
        return f"<Voucher id={self.id} tier={self.voucher_tier.value}>"


class BoosterPack(db.Model):
    """Datos específicos de los Booster Packs (sobres comprables en la tienda).

    A diferencia de los items individuales, los Booster Packs son contenedores
    que al abrirse ofrecen al jugador varias cartas entre las que elegir. Se
    organizan en 5 categorías (Arcana, Celestial, Standard, Buffoon, Spectral)
    según qué tipo de carta contienen, y 3 tamaños (Normal, Jumbo, Mega) que
    determinan precio y cantidad de opciones, totalizando 15 packs distintos
    en el juego base.

    Aunque los Booster Packs no se "desbloquean" en el sentido tradicional
    (siempre están disponibles desde el inicio del juego), se modelan dentro
    de la jerarquía de Unlockables por simetría arquitectónica y para
    aprovechar los campos comunes (nombre, descripción, imagen, wiki_url).
    """

    __tablename__ = "booster_packs"

    id = db.Column(db.Integer, db.ForeignKey("unlockables.id"), primary_key=True)

    pack_type = db.Column(
        db.Enum(BoosterPackType, name="booster_pack_type"),
        nullable=False,
        index=True,
    )
    size = db.Column(
        db.Enum(BoosterPackSize, name="booster_pack_size"),
        nullable=False,
        index=True,
    )
    cost = db.Column(db.SmallInteger, nullable=False, index=True)

    unlockable = db.relationship("Unlockable", back_populates="booster_pack")

    def __repr__(self) -> str:
        return (
            f"<BoosterPack id={self.id} "
            f"{self.pack_type.value} {self.size.value} ${self.cost}>"
        )


class ChallengeDeck(db.Model):
    """Datos específicos de los Challenge Decks (modos de juego con desafío).

    A diferencia de las barajas regulares, los Challenge Decks son modos
    especiales que combinan una baraja inicial (a menudo modificada), un
    conjunto de reglas alteradas (modifier), items iniciales pre-redimidos
    (starter) y restricciones sobre qué items pueden aparecer (banned).

    Decisión de modelado: los campos descriptivos se almacenan como TEXT
    plano (renderizado del wikitexto). Una alternativa "perfecta" sería
    crear tablas pivote relacionando cada challenge con los items concretos
    que prohíbe o entrega, pero la complejidad es desproporcionada al
    alcance del TFG y los textos renderizados son perfectamente útiles
    para mostrar al usuario.

    Mecánica de desbloqueo: los Challenge Decks no tienen un unlock_condition
    individual en la fuente — la wiki documenta que los primeros 5 se
    desbloquean al ganar con 5 barajas distintas y los siguientes 15 al
    completar Challenge Decks previos. El campo `unlock_condition` del padre
    Unlockable se rellena con un texto descriptivo común para todos.
    """

    __tablename__ = "challenge_decks"

    id = db.Column(db.Integer, db.ForeignKey("unlockables.id"), primary_key=True)

    # Modificadores de reglas del challenge (siempre presente)
    modifier = db.Column(db.Text, nullable=False)
    # Items iniciales pre-redimidos (jokers, tarots, vouchers); puede ser NULL
    starter = db.Column(db.Text, nullable=True)
    # Items prohibidos durante la partida; puede ser NULL
    banned = db.Column(db.Text, nullable=True)
    # Modificación de la baraja base (p.ej. "Ranks 2-9 only, 32 cards total");
    # NULL significa que se usa la baraja estándar de 52 cartas
    deck_description = db.Column(db.Text, nullable=True)

    unlockable = db.relationship("Unlockable", back_populates="challenge_deck")

    def __repr__(self) -> str:
        name = self.unlockable.name if self.unlockable else "?"
        return f"<ChallengeDeck id={self.id} name={name!r}>"
