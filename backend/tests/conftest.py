"""Configuración compartida de pytest para todos los tests del backend.

Las fixtures definidas aquí (decoradas con ``@pytest.fixture``) están
disponibles automáticamente en cualquier test del directorio sin necesidad
de importarlas. Esto sigue el patrón estándar de pytest.

Contenido:
  - load_wiki_fixture: cargador de wikitexts de prueba para los scrapers.
  - app / db_session: app Flask + BD SQLite en memoria, aislada por test.
  - sample_user / seeded_achievements / sample_unlockables: datos de dominio
    componibles para los tests del servicio de achievements.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import event

from app import create_app
from app.config import Config
from app.extensions import db


# =============================================================================
# Cargador de fixtures de wikitext (para tests de scrapers)
# =============================================================================


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "wiki"


@pytest.fixture
def load_wiki_fixture():
    """Devuelve una función para cargar wikitext de fixtures por nombre.

    Uso en un test::

        def test_algo(load_wiki_fixture):
            wikitext = load_wiki_fixture("joker")
            ...

    Los archivos viven en ``tests/fixtures/wiki/<name>.txt`` con codificación
    UTF-8 (necesaria para caracteres especiales del wikitext).
    """

    def _load(name: str) -> str:
        path = FIXTURES_DIR / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"Fixture not found: {path}. "
                f"¿Olvidaste ejecutar _create_wiki_fixtures.py?"
            )
        return path.read_text(encoding="utf-8")

    return _load


# =============================================================================
# Configuración Flask para tests
# =============================================================================


class TestConfig(Config):
    """Override de Config para tests: BD SQLite en memoria, sin rate-limiting."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SECRET_KEY = "test-secret-key"
    CORS_ORIGINS = ["*"]
    STEAM_API_KEY = "test-steam-api-key"
    RATELIMIT_ENABLED = False
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


@pytest.fixture(scope="session")
def app():
    """Aplicación Flask configurada para tests (session-scoped).

    El listener de PRAGMA foreign_keys=ON se registra DENTRO del app_context
    porque en Flask-SQLAlchemy 3.x acceder a `db.engine` fuera de contexto
    lanza RuntimeError. Esto fuerza FK enforcement en SQLite, que por
    defecto los ignora silenciosamente y ocultaría bugs de ON DELETE
    CASCADE / SET NULL.
    """
    app = create_app(TestConfig)
    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def _enable_sqlite_fk(dbapi_conn, _conn_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        yield app


@pytest.fixture
def db_session(app):
    """Sesión SQLAlchemy fresca por test, con esquema recreado.

    Crea el esquema completo desde los modelos (NO usa migraciones Alembic
    — eso sería más fiel a producción pero también órdenes de magnitud más
    lento). Drop al final para aislar.
    """
    db.create_all()
    yield db.session
    db.session.remove()
    db.drop_all()


# =============================================================================
# Fixtures de datos de dominio
# =============================================================================


@pytest.fixture
def sample_user(db_session):
    """Un usuario de prueba mínimo con firebase_uid."""
    from app.models import User

    user = User(
        firebase_uid="test-firebase-uid",
        display_name="TestUser",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def seeded_achievements(db_session):
    """Subset de unlock_factors y achievements relevantes para los tests."""
    from app.models import Achievement, UnlockFactor

    factors_data = [
        ("REACH_ANTE_4",             "Reach Ante 4."),
        ("COMPLETE_ALL_CHALLENGES",  "Complete every challenge run."),
        ("DISCOVER_100_PERCENT",     "Discover 100% of your collection."),
        ("WIN_ALL_DECKS_GOLD_STAKE", "Win with every deck at Gold Stake difficulty."),
        ("GOLD_STICKER_ALL_JOKERS",  "Earn a Gold Sticker on every Joker."),
    ]
    factors: dict[str, UnlockFactor] = {}
    for code, description in factors_data:
        factor = UnlockFactor(code=code, description=description)
        db_session.add(factor)
        factors[code] = factor
    db_session.flush()

    achievements_data = [
        ("BAL_01", "Ante Up!",        "REACH_ANTE_4"),
        ("BAL_23", "Rule Breaker",    "COMPLETE_ALL_CHALLENGES"),
        ("BAL_29", "Completionist",   "DISCOVER_100_PERCENT"),
        ("BAL_30", "Completionist+",  "WIN_ALL_DECKS_GOLD_STAKE"),
        ("BAL_31", "Completionist++", "GOLD_STICKER_ALL_JOKERS"),
    ]
    achievements: dict[str, Achievement] = {}
    for steam_api_name, name, factor_code in achievements_data:
        ach = Achievement(
            steam_api_name=steam_api_name,
            name=name,
            description=f"Test achievement {steam_api_name}",
            hidden=False,
            unlock_factor=factors[factor_code],
        )
        db_session.add(ach)
        achievements[steam_api_name] = ach
    db_session.commit()

    return {"factors": factors, "achievements": achievements}


@pytest.fixture
def sample_unlockables(db_session, seeded_achievements):
    """Set mínimo de unlockables para ejercitar los resolvers.

    Crea:
      - 2 jokers: Showman (shared factor REACH_ANTE_4) y Joker base sin factor
      - 2 decks: Red Deck, Blue Deck (sin factor)
      - 3 challenge_decks (sin factor)

    DECISIÓN: solo creamos filas en la tabla padre `unlockables`, sin instanciar
    las filas hijas en `jokers`, `decks`, etc. El servicio de achievements
    consulta exclusivamente la tabla padre (vía Unlockable.type filter), y los
    resolvers no necesitan los campos específicos de cada subclase. Esto
    simplifica drásticamente la fixture y la hace más rápida.

    El modelo Unlockable NO tiene polymorphic_identity configurado (es joined
    inheritance "manual"), por lo que `type` se setea explícitamente en cada
    instanciación.

    Si en el futuro hace falta probar lógica que requiera Joker.rarity o
    similar, basta con añadir el subobjeto via la relación 1:1:
        showman.joker = Joker(rarity=JokerRarity.UNCOMMON, in_shop=True, ...)
    El cascade="all, delete-orphan" del padre se encarga del INSERT.
    """
    from app.models import Unlockable, UnlockableType

    factors = seeded_achievements["factors"]

    showman = Unlockable(
        type=UnlockableType.JOKER,
        item_number=114,
        name="Showman",
        unlock_condition="Reach Ante 4.",
        unlock_factor=factors["REACH_ANTE_4"],
    )
    base_joker = Unlockable(
        type=UnlockableType.JOKER,
        item_number=1,
        name="Joker",
    )

    red_deck = Unlockable(
        type=UnlockableType.DECK,
        item_number=1,
        name="Red Deck",
    )
    blue_deck = Unlockable(
        type=UnlockableType.DECK,
        item_number=2,
        name="Blue Deck",
    )

    ch1 = Unlockable(
        type=UnlockableType.CHALLENGE_DECK,
        item_number=1,
        name="The Omelette",
    )
    ch2 = Unlockable(
        type=UnlockableType.CHALLENGE_DECK,
        item_number=2,
        name="On a Knife's Edge",
    )
    ch3 = Unlockable(
        type=UnlockableType.CHALLENGE_DECK,
        item_number=3,
        name="X-Ray Vision",
    )

    for obj in [showman, base_joker, red_deck, blue_deck, ch1, ch2, ch3]:
        db_session.add(obj)
    db_session.commit()

    return {
        "showman": showman,
        "base_joker": base_joker,
        "jokers": [showman, base_joker],
        "decks": [red_deck, blue_deck],
        "challenges": [ch1, ch2, ch3],
    }