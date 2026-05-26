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

    base_u = Unlockable(type=UnlockableType.JOKER, item_number=1, name="Joker")
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
def user_with_progress(db_session, sample_user, populated_catalog, seeded_achievements):
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

    db_session.add(
        UserUnlock(
            user_id=sample_user.id,
            unlockable_id=showman.id,
            unlocked=True,
            unlocked_at=when,
            source=UnlockSource.STEAM_SYNC,
        )
    )
    db_session.add(
        UserStickerApplication(
            user_id=sample_user.id,
            unlockable_id=showman.id,
            highest_stake_order=8,
            earned_at=when,
            source=UnlockSource.STEAM_SYNC,
        )
    )
    db_session.add(
        UserUnlock(
            user_id=sample_user.id,
            unlockable_id=red_deck.id,
            unlocked=True,
            unlocked_at=when,
            source=UnlockSource.STEAM_SYNC,
        )
    )
    db_session.add(
        UserStickerApplication(
            user_id=sample_user.id,
            unlockable_id=red_deck.id,
            highest_stake_order=8,
            earned_at=when,
            source=UnlockSource.STEAM_SYNC,
        )
    )
    db_session.add(
        UserAchievement(
            user_id=sample_user.id,
            achievement_id=ante_up.id,
            unlocked=True,
            unlocked_at=when,
            source=UnlockSource.STEAM_SYNC,
        )
    )
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

    def test_overlay_fields_present(self, client, auth_headers, seeded_achievements):
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
        rule_breaker = next(it for it in items if it["steam_api_name"] == "BAL_23")
        assert rule_breaker["unlocked_for_me"] is False
        assert rule_breaker["unlocked_at"] is None


# =============================================================================
# POST /api/me/unlocks (botón "marcar como desbloqueado")
# =============================================================================


class TestSetUnlockEndpoint:
    """Tests del endpoint POST /api/me/unlocks.

    Cubre el contrato completo del endpoint que sustenta el botón
    "marcar como desbloqueado" del frontend (Jokers / Consumibles /
    Colección) y el futuro Steam-sync (compartirán el mismo upsert
    interno vía `services/unlocks_service.set_unlock_for_user`).
    """

    def test_missing_auth_returns_401(self, client, populated_catalog):
        """Sin token → 401, igual que el resto de /api/me/*."""
        showman = populated_catalog["showman"]
        resp = client.post(
            "/api/me/unlocks",
            json={"unlockable_id": showman.id},
        )
        assert resp.status_code == 401

    def test_creates_new_unlock_for_user(
        self, client, auth_headers, sample_user, populated_catalog, db_session
    ):
        """Si no hay UserUnlock previo, lo crea y devuelve overlay True."""
        showman = populated_catalog["showman"]
        unlockable_id = showman.id

        pre = (
            db_session.query(UserUnlock)
            .filter_by(user_id=sample_user.id, unlockable_id=unlockable_id)
            .one_or_none()
        )
        assert pre is None

        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": unlockable_id},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["unlocked_for_me"] is True
        assert data["unlocked_at"] is not None

        # Y la fila aparece en BD.
        post = (
            db_session.query(UserUnlock)
            .filter_by(user_id=sample_user.id, unlockable_id=unlockable_id)
            .one()
        )
        assert post.unlocked is True
        assert post.source == UnlockSource.MANUAL

    def test_idempotent_remark_same_state_preserves_unlocked_at(
        self, client, auth_headers, sample_user, user_with_progress, db_session
    ):
        """Re-marcar lo ya desbloqueado responde 200 sin tocar `unlocked_at`.

        Esto es importante para el lifecycle de la fila: si el usuario
        pulsa dos veces el botón sin querer, el primer timestamp no se
        debe perder (sería confuso ver el desbloqueo "actualizado" a
        ahora cuando en realidad pasó hace meses).
        """
        existing = (
            db_session.query(UserUnlock)
            .filter_by(user_id=sample_user.id)
            .filter(UserUnlock.unlocked.is_(True))
            .first()
        )
        assert existing is not None
        original_when = existing.unlocked_at
        original_source = existing.source

        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": existing.unlockable_id, "unlocked": True},
        )
        assert resp.status_code == 200
        assert resp.get_json()["unlocked_for_me"] is True

        db_session.refresh(existing)
        assert existing.unlocked_at == original_when
        # El source tampoco debe sobreescribirse — un re-mark MANUAL
        # sobre un STEAM_SYNC NO debería pisar el origen original.
        assert existing.source == original_source

    def test_can_flip_to_unlocked_false(
        self, client, auth_headers, user_with_progress, db_session
    ):
        """Pasar `unlocked: false` desbloquea la fila y limpia el timestamp."""
        existing = (
            db_session.query(UserUnlock).filter(UserUnlock.unlocked.is_(True)).first()
        )
        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": existing.unlockable_id, "unlocked": False},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["unlocked_for_me"] is False
        assert data["unlocked_at"] is None
        db_session.refresh(existing)
        assert existing.unlocked is False
        assert existing.unlocked_at is None

    def test_unknown_unlockable_returns_404(
        self, client, auth_headers, populated_catalog
    ):
        """unlockable_id que no existe en BD → 404 limpio, no IntegrityError."""
        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": 999999},
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "not_found"
        assert "999999" in data["message"]

    def test_missing_unlockable_id_returns_400(self, client, auth_headers):
        resp = client.post("/api/me/unlocks", headers=auth_headers, json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "unlockable_id" in data["details"]

    def test_non_int_unlockable_id_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": "abc"},
        )
        assert resp.status_code == 400
        assert "unlockable_id" in resp.get_json()["details"]

    def test_bool_unlockable_id_rejected(self, client, auth_headers):
        """`unlockable_id=True` NO debe colar como 1 — bool es subclase
        de int en Python pero semánticamente es un payload inválido."""
        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": True},
        )
        assert resp.status_code == 400
        assert "unlockable_id" in resp.get_json()["details"]

    def test_non_bool_unlocked_returns_400(
        self, client, auth_headers, populated_catalog
    ):
        showman = populated_catalog["showman"]
        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={
                "unlockable_id": showman.id,
                "unlocked": "yes",
            },
        )
        assert resp.status_code == 400
        assert "unlocked" in resp.get_json()["details"]

    def test_user_isolation(
        self, client, auth_headers, sample_user, populated_catalog, db_session
    ):
        """El unlock se asocia al usuario del token, no a otros usuarios
        que existan en BD. Verifica que `g.user.id` es la fuente de verdad."""
        from app.models import User

        other = User(firebase_uid="other-uid", display_name="Other")
        db_session.add(other)
        db_session.commit()

        showman = populated_catalog["showman"]
        resp = client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": showman.id},
        )
        assert resp.status_code == 200

        unlocks = db_session.query(UserUnlock).filter_by(unlockable_id=showman.id).all()
        assert len(unlocks) == 1
        assert unlocks[0].user_id == sample_user.id

    def test_overlay_visible_immediately_in_my_jokers(
        self, client, auth_headers, sample_user, populated_catalog, db_session
    ):
        """Tras marcar manualmente, /api/me/jokers ya devuelve
        unlocked_for_me=true sin necesidad de re-fetch del frontend.

        Verifica end-to-end que el upsert MANUAL produce el mismo
        overlay que un STEAM_SYNC — confirma que el contrato del
        endpoint compartido se cumple."""
        showman = populated_catalog["showman"]
        client.post(
            "/api/me/unlocks",
            headers=auth_headers,
            json={"unlockable_id": showman.id},
        )

        resp = client.get("/api/me/jokers", headers=auth_headers)
        items = resp.get_json()["items"]
        showman_overlay = next(it for it in items if it["name"] == "Showman")
        assert showman_overlay["unlocked_for_me"] is True
        assert showman_overlay["unlocked_at"] is not None


# =============================================================================
# POST /api/me/achievements/unlock (botón "marcar como desbloqueado")
# =============================================================================


class TestSetAchievementUnlockEndpoint:
    """Tests del endpoint POST /api/me/achievements/unlock.

    Cubre el contrato del endpoint hermano de POST /api/me/unlocks
    pensado para achievements (que NO son Unlockable y viven en su
    propia tabla con su propio pivot UserAchievement).
    """

    def test_missing_auth_returns_401(self, client, seeded_achievements):
        ante_up = seeded_achievements["achievements"]["BAL_01"]
        resp = client.post(
            "/api/me/achievements/unlock",
            json={"achievement_id": ante_up.id},
        )
        assert resp.status_code == 401

    def test_creates_new_unlock_for_user(
        self, client, auth_headers, sample_user, seeded_achievements, db_session
    ):
        """Si no hay UserAchievement previo, lo crea y devuelve overlay True."""
        ante_up = seeded_achievements["achievements"]["BAL_01"]

        pre = (
            db_session.query(UserAchievement)
            .filter_by(user_id=sample_user.id, achievement_id=ante_up.id)
            .one_or_none()
        )
        assert pre is None

        resp = client.post(
            "/api/me/achievements/unlock",
            headers=auth_headers,
            json={"achievement_id": ante_up.id},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["unlocked_for_me"] is True
        assert data["unlocked_at"] is not None
        assert data["was_already_unlocked"] is False

        post = (
            db_session.query(UserAchievement)
            .filter_by(user_id=sample_user.id, achievement_id=ante_up.id)
            .one()
        )
        assert post.unlocked is True
        assert post.source == UnlockSource.MANUAL

    def test_idempotent_remark_reports_was_already_unlocked(
        self, client, auth_headers, user_with_progress, seeded_achievements, db_session
    ):
        """Re-marcar un achievement ya desbloqueado responde 200 + flag.

        A diferencia de /api/me/unlocks (que es totalmente silencioso),
        aquí devolvemos `was_already_unlocked=true` porque el service
        de achievements maneja cascadas — un caller interno (Steam
        sync logger) puede querer distinguir "se desbloqueó X y
        cascadeó N items" vs "ya estaba desbloqueado, sin cambios".
        """
        ante_up = seeded_achievements["achievements"]["BAL_01"]
        existing = (
            db_session.query(UserAchievement).filter_by(achievement_id=ante_up.id).one()
        )
        original_when = existing.unlocked_at
        original_source = existing.source

        resp = client.post(
            "/api/me/achievements/unlock",
            headers=auth_headers,
            json={"achievement_id": ante_up.id},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["unlocked_for_me"] is True
        assert data["was_already_unlocked"] is True

        db_session.refresh(existing)
        assert existing.unlocked_at == original_when
        # source preservado igual que en /api/me/unlocks: un MANUAL
        # no-op NO debe sobreescribir un STEAM_SYNC histórico.
        assert existing.source == original_source

    def test_unknown_achievement_returns_404(
        self, client, auth_headers, seeded_achievements
    ):
        """achievement_id inexistente → 404 limpio (no ValueError sin
        capturar). Traducción de `ValueError` del service a HTTP."""
        resp = client.post(
            "/api/me/achievements/unlock",
            headers=auth_headers,
            json={"achievement_id": 999999},
        )
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "not_found"
        assert "999999" in data["message"]

    def test_missing_achievement_id_returns_400(self, client, auth_headers):
        resp = client.post("/api/me/achievements/unlock", headers=auth_headers, json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "achievement_id" in data["details"]

    def test_non_int_achievement_id_returns_400(self, client, auth_headers):
        resp = client.post(
            "/api/me/achievements/unlock",
            headers=auth_headers,
            json={"achievement_id": "abc"},
        )
        assert resp.status_code == 400
        assert "achievement_id" in resp.get_json()["details"]

    def test_bool_achievement_id_rejected(self, client, auth_headers):
        """Misma defensa que el endpoint de unlocks: bool es subclass
        de int en Python, lo rechazamos explícitamente."""
        resp = client.post(
            "/api/me/achievements/unlock",
            headers=auth_headers,
            json={"achievement_id": True},
        )
        assert resp.status_code == 400
        assert "achievement_id" in resp.get_json()["details"]

    def test_overlay_visible_immediately_in_my_achievements(
        self, client, auth_headers, sample_user, seeded_achievements
    ):
        """Tras marcar manualmente, GET /api/me/achievements ya devuelve
        unlocked_for_me=true sin re-fetch. Confirma que el upsert
        MANUAL produce el mismo overlay que un STEAM_SYNC."""
        ante_up = seeded_achievements["achievements"]["BAL_01"]
        client.post(
            "/api/me/achievements/unlock",
            headers=auth_headers,
            json={"achievement_id": ante_up.id},
        )

        resp = client.get("/api/me/achievements", headers=auth_headers)
        items = resp.get_json()["items"]
        ante_up_overlay = next(it for it in items if it["steam_api_name"] == "BAL_01")
        assert ante_up_overlay["unlocked_for_me"] is True
        assert ante_up_overlay["unlocked_at"] is not None
