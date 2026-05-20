"""Tests para los endpoints autenticados /api/me/*.

Cobertura:
  - Auth gating: 401 sin token, con header malformado, con token vacío.
  - 200 con token mockeado (Firebase no se inicializa en TestConfig).
  - /api/me/summary devuelve counts/percentages correctos para usuario
    vacío y para usuario con progreso simulado.
  - /api/me/jokers, /me/decks, /me/achievements devuelven overlay
    (unlocked_for_me, unlocked_at, highest_stake_order) consistente
    con los datos seedeados.

Estrategia de mocking: el decorator @require_auth llama a
firebase_auth.verify_id_token. En tests parchamos esa función para que
devuelva un dict como el que devolvería Firebase tras verificar un token
real, sin necesidad de credenciales reales.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.models import (
    Achievement,
    ChallengeDeck,
    Deck,
    Joker,
    Unlockable,
    UnlockableType,
    UserAchievement,
    UserStickerApplication,
    UserUnlock,
)
from app.models.enums import JokerRarity, UnlockSource


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client(app):
    """Test client HTTP de Flask."""
    return app.test_client()


@pytest.fixture
def populated_catalog(db_session, seeded_achievements):
    """Catálogo poblado (idéntico al de test_catalog_endpoints.py).

    Duplicado intencionalmente para que este archivo de tests sea
    autocontenido y se pueda mover/extraer sin tocar el otro.
    """
    factors = seeded_achievements["factors"]

    showman_u = Unlockable(
        type=UnlockableType.JOKER,
        item_number=114,
        name="Showman",
        unlock_condition="Reach Ante 4.",
        unlock_factor=factors["REACH_ANTE_4"],
    )
    showman_u.joker = Joker(
        rarity=JokerRarity.UNCOMMON,
        in_shop=True,
        has_negative_variant=False,
        is_copyable=False,
        is_perishable=False,
        is_eternal=False,
    )

    base_u = Unlockable(
        type=UnlockableType.JOKER, item_number=1, name="Joker"
    )
    base_u.joker = Joker(
        rarity=JokerRarity.COMMON,
        in_shop=True,
        has_negative_variant=False,
        is_copyable=False,
        is_perishable=False,
        is_eternal=False,
    )

    red_u = Unlockable(type=UnlockableType.DECK, item_number=1, name="Red Deck")
    red_u.deck = Deck()
    blue_u = Unlockable(type=UnlockableType.DECK, item_number=2, name="Blue Deck")
    blue_u.deck = Deck()

    omelette_u = Unlockable(
        type=UnlockableType.CHALLENGE_DECK, item_number=1, name="The Omelette"
    )
    omelette_u.challenge_deck = ChallengeDeck(modifier="No vouchers")

    for obj in [showman_u, base_u, red_u, blue_u, omelette_u]:
        db_session.add(obj)
    db_session.commit()

    return {
        "showman": showman_u.joker,
        "base_joker": base_u.joker,
        "red_deck": red_u.deck,
        "blue_deck": blue_u.deck,
        "challenge": omelette_u.challenge_deck,
    }


@pytest.fixture
def auth_headers(sample_user):
    """Mocks firebase verify_id_token para que devuelva el sample_user.

    El decorator @require_auth llama a firebase_auth.verify_id_token con
    el token del header; aquí lo parchamos para que devuelva el decoded
    token con el firebase_uid del sample_user existente.
    """
    headers = {"Authorization": "Bearer fake-test-token"}
    patcher = patch("app.api.auth.firebase_auth.verify_id_token")
    mock_verify = patcher.start()
    mock_verify.return_value = {
        "uid": sample_user.firebase_uid,
        "email": sample_user.email,
        "name": sample_user.display_name,
        "picture": sample_user.avatar_url,
    }
    yield headers
    patcher.stop()


@pytest.fixture
def user_with_progress(
    db_session, sample_user, populated_catalog, seeded_achievements
):
    """sample_user con algunos unlocks + sticker + achievement marcados.

    Crea:
      - UserUnlock para Showman (joker)
      - UserStickerApplication Gold (stake=8) para Showman
      - UserUnlock para Red Deck
      - UserStickerApplication Gold para Red Deck (vía Completionist+)
      - UserAchievement para Ante Up! (BAL_01)

    Devuelve el sample_user para referencia.
    """
    when = datetime.now(timezone.utc)
    showman = populated_catalog["showman"]
    red_deck = populated_catalog["red_deck"]
    ante_up = seeded_achievements["achievements"]["BAL_01"]

    db_session.add(UserUnlock(
        user_id=sample_user.id,
        unlockable_id=showman.id,
        unlocked=True,
        unlocked_at=when,
        source=UnlockSource.STEAM_SYNC,
    ))
    db_session.add(UserStickerApplication(
        user_id=sample_user.id,
        unlockable_id=showman.id,
        highest_stake_order=8,
        earned_at=when,
        source=UnlockSource.STEAM_SYNC,
    ))
    db_session.add(UserUnlock(
        user_id=sample_user.id,
        unlockable_id=red_deck.id,
        unlocked=True,
        unlocked_at=when,
        source=UnlockSource.STEAM_SYNC,
    ))
    db_session.add(UserStickerApplication(
        user_id=sample_user.id,
        unlockable_id=red_deck.id,
        highest_stake_order=8,
        earned_at=when,
        source=UnlockSource.STEAM_SYNC,
    ))
    db_session.add(UserAchievement(
        user_id=sample_user.id,
        achievement_id=ante_up.id,
        unlocked=True,
        unlocked_at=when,
        source=UnlockSource.STEAM_SYNC,
    ))
    db_session.commit()
    return sample_user


# =============================================================================
# Auth gating
# =============================================================================


class TestAuthGating:
    """Todos los endpoints /api/me/* requieren token Firebase válido."""

    @pytest.mark.parametrize(
        "path",
        ["/api/me/summary", "/api/me/jokers", "/api/me/decks", "/api/me/achievements"],
    )
    def test_missing_authorization_header_returns_401(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "path",
        ["/api/me/summary", "/api/me/jokers", "/api/me/decks", "/api/me/achievements"],
    )
    def test_malformed_authorization_header_returns_401(self, client, path):
        resp = client.get(path, headers={"Authorization": "NotBearer xyz"})
        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "path",
        ["/api/me/summary", "/api/me/jokers", "/api/me/decks", "/api/me/achievements"],
    )
    def test_empty_bearer_token_returns_401(self, client, path):
        resp = client.get(path, headers={"Authorization": "Bearer "})
        assert resp.status_code == 401


# =============================================================================
# /api/me/summary
# =============================================================================


class TestSummaryEndpoint:
    """Tests del endpoint agregador /api/me/summary."""

    def test_empty_user_returns_zeros(
        self, client, auth_headers, populated_catalog, seeded_achievements
    ):
        """Sin progreso, todos los percentages son 0 pero los totales del
        catálogo se calculan correctamente."""
        resp = client.get("/api/me/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()

        assert data["by_type"]["JOKER"]["total"] == 2
        assert data["by_type"]["JOKER"]["unlocked"] == 0
        assert data["by_type"]["JOKER"]["percent"] == 0.0
        assert data["by_type"]["DECK"]["total"] == 2
        assert data["by_type"]["DECK"]["unlocked"] == 0
        assert data["achievements"]["total"] == 5  # seeded_achievements
        assert data["achievements"]["unlocked"] == 0
        assert data["gold_stickers"]["total"] == 0

    def test_with_progress_reflects_unlocks_and_stickers(
        self, client, auth_headers, user_with_progress
    ):
        """Con 1 joker + 1 deck + 1 achievement desbloqueados y Gold
        Sticker en ambos items, el summary lo refleja correctamente."""
        resp = client.get("/api/me/summary", headers=auth_headers)
        data = resp.get_json()

        assert data["by_type"]["JOKER"]["unlocked"] == 1
        assert data["by_type"]["JOKER"]["percent"] == 50.0  # 1/2
        assert data["by_type"]["DECK"]["unlocked"] == 1
        assert data["by_type"]["DECK"]["percent"] == 50.0
        assert data["achievements"]["unlocked"] == 1
        assert data["achievements"]["percent"] == 20.0  # 1/5
        assert data["gold_stickers"]["jokers"] == 1
        assert data["gold_stickers"]["decks"] == 1
        assert data["gold_stickers"]["total"] == 2


# =============================================================================
# /api/me/jokers
# =============================================================================


class TestMyJokersEndpoint:
    """Tests del endpoint /api/me/jokers (catálogo + overlay)."""

    def test_returns_overlay_fields_on_each_item(
        self, client, auth_headers, populated_catalog
    ):
        """Sin progreso, los overlays vienen pero todos false/null."""
        resp = client.get("/api/me/jokers", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        for item in data["items"]:
            assert "unlocked_for_me" in item
            assert "unlocked_at" in item
            assert "highest_stake_order" in item
            assert item["unlocked_for_me"] is False
            assert item["unlocked_at"] is None
            assert item["highest_stake_order"] is None

    def test_unlocked_joker_shows_overlay_true(
        self, client, auth_headers, user_with_progress, populated_catalog
    ):
        resp = client.get("/api/me/jokers", headers=auth_headers)
        items = resp.get_json()["items"]
        showman = next(it for it in items if it["name"] == "Showman")
        assert showman["unlocked_for_me"] is True
        assert showman["unlocked_at"] is not None
        assert showman["highest_stake_order"] == 8  # Gold Sticker

    def test_non_unlocked_joker_shows_overlay_false(
        self, client, auth_headers, user_with_progress, populated_catalog
    ):
        """El joker base (no desbloqueado) sigue con overlay false."""
        resp = client.get("/api/me/jokers", headers=auth_headers)
        items = resp.get_json()["items"]
        base = next(it for it in items if it["name"] == "Joker")
        assert base["unlocked_for_me"] is False
        assert base["highest_stake_order"] is None


# =============================================================================
# /api/me/decks
# =============================================================================


class TestMyDecksEndpoint:
    """Tests del endpoint /api/me/decks."""

    def test_overlay_includes_sticker_for_decks(
        self, client, auth_headers, user_with_progress, populated_catalog
    ):
        """Las decks también pueden tener Gold Sticker (Completionist+).
        El overlay debe reflejarlo."""
        resp = client.get("/api/me/decks", headers=auth_headers)
        items = resp.get_json()["items"]
        red = next(it for it in items if it["name"] == "Red Deck")
        assert red["unlocked_for_me"] is True
        assert red["highest_stake_order"] == 8

        blue = next(it for it in items if it["name"] == "Blue Deck")
        assert blue["unlocked_for_me"] is False
        assert blue["highest_stake_order"] is None


# =============================================================================
# /api/me/achievements
# =============================================================================


class TestMyAchievementsEndpoint:
    """Tests del endpoint /api/me/achievements."""

    def test_overlay_fields_present(
        self, client, auth_headers, seeded_achievements
    ):
        resp = client.get("/api/me/achievements", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.get_json()["items"]:
            assert "unlocked_for_me" in item
            assert "unlocked_at" in item
            # achievements no tienen highest_stake_order, NO debe aparecer
            assert "highest_stake_order" not in item

    def test_unlocked_achievement_shows_overlay_true(
        self, client, auth_headers, user_with_progress, seeded_achievements
    ):
        resp = client.get("/api/me/achievements", headers=auth_headers)
        items = resp.get_json()["items"]
        ante_up = next(it for it in items if it["steam_api_name"] == "BAL_01")
        assert ante_up["unlocked_for_me"] is True
        assert ante_up["unlocked_at"] is not None

    def test_non_unlocked_achievement_shows_overlay_false(
        self, client, auth_headers, user_with_progress, seeded_achievements
    ):
        """Los otros 4 achievements seeded siguen sin desbloquear."""
        resp = client.get("/api/me/achievements", headers=auth_headers)
        items = resp.get_json()["items"]
        rule_breaker = next(
            it for it in items if it["steam_api_name"] == "BAL_23"
        )
        assert rule_breaker["unlocked_for_me"] is False
        assert rule_breaker["unlocked_at"] is None