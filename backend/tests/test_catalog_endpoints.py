"""Tests para los endpoints del catálogo público.

Cobertura:
  - Paginación (response shape, per_page, total_pages, page out of range).
  - Filtrado (whitelist, valores válidos, valores inválidos → 400).
  - Ordenamiento (asc, desc con `-`, campo inválido → 400).
  - Detalle por id (200 + 404 con JSON consistente).
  - Error handlers globales (404 de ruta inexistente, ValidationError).

Cubre los endpoints principales (jokers, decks, challenge-decks,
achievements) que ejercitan los tres patrones de query:
  - CTI subclass con filtros (jokers).
  - CTI subclass sin filtros (decks, challenge-decks).
  - Tabla flat con nested (achievements).

Los endpoints de reference data (blinds, tags, stakes, etc.) usan
exactamente el mismo helper de paginación/filtrado, por lo que verificar
uno equivale a verificar todos para el comportamiento del helper.
"""
from __future__ import annotations

import pytest

from app.models import (
    ChallengeDeck,
    Consumable,
    Deck,
    Joker,
    Unlockable,
    UnlockableType,
)
from app.models.enums import JokerRarity


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client(app):
    """Test client HTTP de Flask."""
    return app.test_client()


@pytest.fixture
def populated_catalog(db_session, seeded_achievements):
    """Catálogo poblado con filas padre+hija para que los endpoints las
    encuentren (los endpoints queryan las subclases, no Unlockable padre).

    Crea:
      - 3 jokers (COMMON, UNCOMMON, RARE) para tests de filtros.
      - 2 decks (Red, Blue).
      - 2 challenge decks (Omelette, Knife's Edge).
    """
    factors = seeded_achievements["factors"]

    # Jokers
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
        type=UnlockableType.JOKER,
        item_number=1,
        name="Joker",
    )
    base_u.joker = Joker(
        rarity=JokerRarity.COMMON,
        in_shop=True,
        has_negative_variant=False,
        is_copyable=False,
        is_perishable=False,
        is_eternal=False,
    )

    blueprint_u = Unlockable(
        type=UnlockableType.JOKER,
        item_number=14,
        name="Blueprint",
        unlock_condition="Win a Run.",
    )
    blueprint_u.joker = Joker(
        rarity=JokerRarity.RARE,
        in_shop=True,
        has_negative_variant=False,
        is_copyable=False,
        is_perishable=False,
        is_eternal=False,
    )

    # Decks
    red_u = Unlockable(type=UnlockableType.DECK, item_number=1, name="Red Deck")
    red_u.deck = Deck()
    blue_u = Unlockable(type=UnlockableType.DECK, item_number=2, name="Blue Deck")
    blue_u.deck = Deck()

    # Challenge decks
    omelette_u = Unlockable(
        type=UnlockableType.CHALLENGE_DECK,
        item_number=1,
        name="The Omelette",
    )
    omelette_u.challenge_deck = ChallengeDeck(modifier="No vouchers")

    knife_u = Unlockable(
        type=UnlockableType.CHALLENGE_DECK,
        item_number=2,
        name="On a Knife's Edge",
    )
    knife_u.challenge_deck = ChallengeDeck(modifier="Hard mode")

    for obj in [showman_u, base_u, blueprint_u, red_u, blue_u, omelette_u, knife_u]:
        db_session.add(obj)
    db_session.commit()

    return {
        "jokers": [base_u.joker, blueprint_u.joker, showman_u.joker],
        "decks": [red_u.deck, blue_u.deck],
        "challenges": [omelette_u.challenge_deck, knife_u.challenge_deck],
    }


# =============================================================================
# Tests del endpoint /api/jokers (ejercita el patrón CTI con filtros)
# =============================================================================


class TestJokersListEndpoint:
    """Tests de /api/jokers (list)."""

    def test_returns_paginated_response_shape(self, client, populated_catalog):
        resp = client.get("/api/jokers")
        assert resp.status_code == 200
        data = resp.get_json()
        for key in ("items", "page", "per_page", "total", "total_pages"):
            assert key in data, f"missing key {key!r}"
        assert data["total"] == 3
        assert data["page"] == 1
        assert len(data["items"]) == 3

    def test_per_page_limits_items(self, client, populated_catalog):
        resp = client.get("/api/jokers?per_page=2")
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["items"]) == 2
        assert data["per_page"] == 2
        assert data["total_pages"] == 2  # 3 items / 2 per page = 2 páginas

    def test_page_offsets_correctly(self, client, populated_catalog):
        page1 = client.get("/api/jokers?per_page=2&page=1").get_json()
        page2 = client.get("/api/jokers?per_page=2&page=2").get_json()
        assert len(page1["items"]) == 2
        assert len(page2["items"]) == 1
        ids_page1 = {item["id"] for item in page1["items"]}
        ids_page2 = {item["id"] for item in page2["items"]}
        assert ids_page1.isdisjoint(ids_page2)

    def test_filter_by_rarity(self, client, populated_catalog):
        resp = client.get("/api/jokers?rarity=COMMON")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["rarity"] == "COMMON"
        assert data["items"][0]["name"] == "Joker"

    def test_filter_with_invalid_value_returns_400(self, client, populated_catalog):
        resp = client.get("/api/jokers?rarity=MEGA_LEGENDARY")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "rarity" in data["details"]

    def test_sort_ascending_by_default(self, client, populated_catalog):
        resp = client.get("/api/jokers?sort=item_number")
        items = resp.get_json()["items"]
        item_numbers = [it["item_number"] for it in items]
        assert item_numbers == sorted(item_numbers)

    def test_sort_descending_with_minus_prefix(self, client, populated_catalog):
        resp = client.get("/api/jokers?sort=-item_number")
        items = resp.get_json()["items"]
        item_numbers = [it["item_number"] for it in items]
        assert item_numbers == sorted(item_numbers, reverse=True)

    def test_sort_invalid_field_returns_400(self, client, populated_catalog):
        resp = client.get("/api/jokers?sort=password")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "sort" in data["details"]

    def test_per_page_too_large_returns_400(self, client, populated_catalog):
        resp = client.get("/api/jokers?per_page=99999")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "per_page" in data["details"]

    def test_per_page_not_integer_returns_400(self, client, populated_catalog):
        resp = client.get("/api/jokers?per_page=abc")
        assert resp.status_code == 400


class TestJokerDetailEndpoint:
    """Tests de /api/jokers/<id>."""

    def test_returns_full_data_when_exists(self, client, populated_catalog):
        showman = populated_catalog["jokers"][2]
        resp = client.get(f"/api/jokers/{showman.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Showman"
        assert data["rarity"] == "UNCOMMON"
        assert data["item_number"] == 114
        # Pull-up del padre Unlockable
        assert data["type"] == "JOKER"
        assert data["unlock_condition"] == "Reach Ante 4."
        # Nested unlock_factor
        assert data["unlock_factor"]["code"] == "REACH_ANTE_4"

    def test_returns_404_when_not_found(self, client, populated_catalog):
        resp = client.get("/api/jokers/999999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "not_found"
        assert "999999" in data["message"]


# =============================================================================
# Tests endpoint /api/consumables (ejercita parser custom de ?type=)
# =============================================================================


@pytest.fixture
def populated_consumables(db_session):
    """Crea un consumable de cada tipo válido (TAROT/PLANET/SPECTRAL).

    Fixture aparte de `populated_catalog` para no añadir dependencias
    cruzadas — los tests de jokers/decks/etc. siguen viendo los mismos
    totales de siempre.
    """
    tarot_u = Unlockable(
        type=UnlockableType.TAROT,
        item_number=1,
        name="The Fool",
    )
    tarot_u.consumable = Consumable(buy_price=3, sell_price=1, in_shop=True)

    planet_u = Unlockable(
        type=UnlockableType.PLANET,
        item_number=1,
        name="Mercury",
    )
    planet_u.consumable = Consumable(buy_price=3, sell_price=1, in_shop=True)

    spectral_u = Unlockable(
        type=UnlockableType.SPECTRAL,
        item_number=1,
        name="Familiar",
    )
    spectral_u.consumable = Consumable(buy_price=4, sell_price=2, in_shop=True)

    for obj in [tarot_u, planet_u, spectral_u]:
        db_session.add(obj)
    db_session.commit()

    return {
        "tarot": tarot_u.consumable,
        "planet": planet_u.consumable,
        "spectral": spectral_u.consumable,
    }


class TestConsumablesTypeFilter:
    """Regression tests para el bug del filtro `?type=` (Mayo 2026).

    Histórico: el parser custom `_parse_consumable_type` usaba
    `UnlockableType(raw)` (lookup por VALUE) mientras `apply_filters`
    en `_helpers.py` usa `Enum[raw]` (lookup por NAME). Como marshmallow
    serializa los enums por NAME por defecto, el frontend reenviaba
    'TAROT' al filtrar y el endpoint respondía 400.

    Estos tests fijan el contrato: NAME funciona (camino natural),
    VALUE también funciona (fallback de robustez) y un valor inválido
    devuelve 400 con la whitelist en el mensaje.
    """

    def test_filter_by_name_returns_only_that_type(
        self, client, populated_consumables
    ):
        """Camino principal: el frontend envía la NAME del enum."""
        resp = client.get("/api/consumables?type=TAROT")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "The Fool"
        assert data["items"][0]["type"] == "TAROT"

    def test_filter_by_value_also_works_as_fallback(
        self, client, populated_consumables
    ):
        """Fallback: si un cliente envía el VALUE en lugar de la NAME,
        el endpoint NO debe romperse. Garantiza robustez ante cambios
        futuros en la convención de serialización del schema."""
        # El VALUE del enum miembro TAROT (cualquier convención de naming
        # que use el modelo; típicamente lowercase). Pasamos por el
        # propio enum para no acoplar el test al string concreto.
        tarot_value = UnlockableType.TAROT.value
        resp = client.get(f"/api/consumables?type={tarot_value}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "The Fool"

    def test_filter_with_invalid_type_returns_400_with_allowed_names(
        self, client, populated_consumables
    ):
        """400 + el mensaje incluye la whitelist de tipos válidos para
        que cualquier discrepancia futura se diagnostique de un vistazo."""
        resp = client.get("/api/consumables?type=NOT_A_REAL_TYPE")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "type" in data["details"]
        # El detalle debe nombrar las opciones válidas.
        detail_text = str(data["details"]["type"])
        assert "TAROT" in detail_text
        assert "PLANET" in detail_text
        assert "SPECTRAL" in detail_text

    def test_filter_rejects_non_consumable_unlockable_type(
        self, client, populated_consumables
    ):
        """JOKER es un UnlockableType válido a nivel del enum, pero NO
        es un consumable. El parser debe rechazarlo con 400, no devolver
        una lista vacía silenciosa."""
        resp = client.get("/api/consumables?type=JOKER")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "type" in data["details"]

    def test_no_type_filter_returns_all_consumables(
        self, client, populated_consumables
    ):
        """Sin `?type=` el endpoint devuelve TODOS los consumables sin
        discriminar. Verifica que el parser solo se invoca cuando el
        cliente provee el parámetro."""
        resp = client.get("/api/consumables")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 3


# =============================================================================
# Tests endpoint /api/decks (ejercita CTI sin filtros propios)
# =============================================================================


class TestDecksEndpoint:
    """Tests de /api/decks."""

    def test_list_returns_all_decks(self, client, populated_catalog):
        resp = client.get("/api/decks")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2

    def test_get_by_id(self, client, populated_catalog):
        red_deck = populated_catalog["decks"][0]
        resp = client.get(f"/api/decks/{red_deck.id}")
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "Red Deck"

    def test_not_found(self, client, populated_catalog):
        resp = client.get("/api/decks/999999")
        assert resp.status_code == 404


# =============================================================================
# Tests endpoint /api/challenge-decks
# =============================================================================


class TestChallengeDecksEndpoint:
    """Tests de /api/challenge-decks."""

    def test_list_includes_modifier(self, client, populated_catalog):
        resp = client.get("/api/challenge-decks")
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        modifiers = {item["modifier"] for item in items}
        assert modifiers == {"No vouchers", "Hard mode"}


# =============================================================================
# Tests endpoint /api/achievements (ejercita tabla flat con nested)
# =============================================================================


class TestAchievementsEndpoint:
    """Tests de /api/achievements."""

    def test_list_includes_nested_unlock_factor(
        self, client, seeded_achievements
    ):
        """El nested unlock_factor debe venir poblado (no requiere round-trip)."""
        resp = client.get("/api/achievements")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 5
        # Cualquier achievement con factor: la rama anterior linkeó los 5.
        items_with_factor = [
            it for it in data["items"] if it.get("unlock_factor") is not None
        ]
        assert len(items_with_factor) == 5
        assert all(
            "code" in it["unlock_factor"] for it in items_with_factor
        )

    def test_get_by_id(self, client, seeded_achievements):
        ante_up = seeded_achievements["achievements"]["BAL_01"]
        resp = client.get(f"/api/achievements/{ante_up.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Ante Up!"
        assert data["unlock_factor"]["code"] == "REACH_ANTE_4"

    def test_default_sort_is_steam_api_name(
        self, client, seeded_achievements
    ):
        resp = client.get("/api/achievements")
        names = [it["steam_api_name"] for it in resp.get_json()["items"]]
        assert names == sorted(names)


# =============================================================================
# Tests de los error handlers globales
# =============================================================================


class TestGlobalErrorHandlers:
    """Verifica que los errores devuelven JSON consistente, no HTML."""

    def test_unknown_route_returns_json_404(self, client):
        resp = client.get("/api/nonexistent-route-xyz")
        assert resp.status_code == 404
        assert resp.is_json
        data = resp.get_json()
        assert data["error"] == "not_found"

    def test_method_not_allowed_returns_json_405(self, client):
        # /api/jokers solo acepta GET; POST debería dar 405 JSON.
        resp = client.post("/api/jokers")
        assert resp.status_code == 405
        assert resp.is_json
        data = resp.get_json()
        assert data["error"] == "method_not_allowed"

    def test_validation_error_has_details(self, client, populated_catalog):
        """Los ValidationError de marshmallow deben incluir `details`
        con info por campo, no solo un mensaje genérico."""
        resp = client.get("/api/jokers?per_page=-5")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "validation_error"
        assert "details" in data
        assert isinstance(data["details"], dict)