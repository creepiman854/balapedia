"""Tests del servicio de sync (app/services/achievement_sync.py).

Inyecta un cliente Steam fake (no usa requests) para verificar el
orquestador, dejando los tests del cliente HTTP en test_steam_client.py.

Cobertura:
  - Validación previa: usuario no existe / usuario sin steam_id.
  - Happy path: shared-factor cascade (Ante Up! -> Showman).
  - Resolvers especiales (Rule Breaker, Completionist+) vía sync.
  - Filtrado de achievements no-achieved.
  - Idempotencia en segundas llamadas.
  - Sync delta (nuevos achievements desde el último sync).
  - Apinames desconocidos van a unknown_apinames (no abortan).
  - Actualización de users.last_steam_sync.
  - Uso del unlocktime de Steam como unlocked_at.
"""

from __future__ import annotations

import pytest

from app.models import (
    User,
    UserAchievement,
    UserStickerApplication,
    UserUnlock,
)
from app.services.achievement_sync import (
    SteamSyncResult,
    UserNotFoundError,
    UserNotLinkedError,
    sync_steam_achievements_for_user,
)
from app.services.steam import SteamAchievement

# =============================================================================
# Helpers
# =============================================================================


def fake_steam_client(achievements: list[SteamAchievement]):
    """Construye un callable que ignora los argumentos y devuelve la lista dada.

    Sirve como sustituto del cliente Steam real para no salir a la red.
    """

    def _client(steam_id, app_id=None, timeout=None):
        return achievements

    return _client


# =============================================================================
# Fixtures locales (no añaden a conftest porque son específicas del sync)
# =============================================================================


@pytest.fixture
def user_with_steam(db_session):
    """User con steam_id vinculado, listo para sync."""
    user = User(
        firebase_uid="test-fb-uid",
        steam_id="76561198000000000",
        display_name="Tester",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def user_without_steam(db_session):
    """User sin steam_id vinculado (solo Firebase)."""
    user = User(
        firebase_uid="other-fb-uid",
        display_name="NoSteamTester",
    )
    db_session.add(user)
    db_session.commit()
    return user


# =============================================================================
# Validación previa: usuario / vinculación
# =============================================================================


class TestValidation:
    """Comprobaciones que se hacen antes de llamar a Steam."""

    def test_user_not_found_raises(self, db_session, seeded_achievements):
        with pytest.raises(UserNotFoundError):
            sync_steam_achievements_for_user(user_id=999_999)

    def test_user_without_steam_id_raises(
        self, db_session, user_without_steam, seeded_achievements
    ):
        with pytest.raises(UserNotLinkedError):
            sync_steam_achievements_for_user(user_id=user_without_steam.id)


# =============================================================================
# Flujo principal y cascada genérica
# =============================================================================


class TestSharedFactorCascade:
    """Verifica que el sync delega correctamente a unlock_achievement_by_code."""

    def test_ante_up_cascades_to_showman(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        """Sync de BAL_01 (Ante Up!) debe desbloquear Showman vía REACH_ANTE_4."""
        client = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_01", achieved=True, unlocktime=1700000000
                ),
            ]
        )

        result = sync_steam_achievements_for_user(
            user_id=user_with_steam.id,
            steam_client_fn=client,
        )

        assert isinstance(result, SteamSyncResult)
        assert result.steam_achievements_received == 1
        assert result.steam_achievements_achieved == 1
        assert result.newly_unlocked_count == 1
        assert result.total_items_cascaded == 1  # Showman

        # UserAchievement registrado en BD
        ua = (
            db_session.query(UserAchievement)
            .filter_by(user_id=user_with_steam.id)
            .one()
        )
        assert ua.unlocked is True

        # Showman tiene su UserUnlock cascaded
        showman = sample_unlockables["showman"]
        uu = (
            db_session.query(UserUnlock)
            .filter_by(user_id=user_with_steam.id, unlockable_id=showman.id)
            .one()
        )
        assert uu.unlocked is True

    def test_unlocked_at_uses_steam_unlocktime(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        """El unlocked_at del UserAchievement viene del unlocktime de Steam,
        no del momento del sync."""
        # unlocktime epoch correspondiente a noviembre 2023
        unlocktime_epoch = 1700000000
        client = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_01", achieved=True, unlocktime=unlocktime_epoch
                ),
            ]
        )

        sync_steam_achievements_for_user(
            user_id=user_with_steam.id,
            steam_client_fn=client,
        )

        ua = (
            db_session.query(UserAchievement)
            .filter_by(user_id=user_with_steam.id)
            .one()
        )
        # Verificamos por componentes: el año del unlocked_at debe ser
        # 2023 (el año del unlocktime), no el año actual del sync.
        # SQLite puede o no preservar tzinfo; tomamos el componente year sin
        # depender de timezone.
        assert ua.unlocked_at.year == 2023

    def test_filters_out_not_achieved_entries(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        """Steam reporta achievements con achieved=0; el sync los ignora."""
        client = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_01", achieved=True, unlocktime=1700000000
                ),
                SteamAchievement(apiname="BAL_23", achieved=False, unlocktime=None),
            ]
        )

        result = sync_steam_achievements_for_user(
            user_id=user_with_steam.id,
            steam_client_fn=client,
        )

        assert result.steam_achievements_received == 2
        assert result.steam_achievements_achieved == 1
        assert result.newly_unlocked_count == 1


# =============================================================================
# Resolvers especiales disparados vía sync
# =============================================================================


class TestSpecialResolversViaSync:
    """Verifica que los resolvers especiales se disparan al sincronizar."""

    def test_rule_breaker_cascades_to_all_challenge_decks(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        client = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_23", achieved=True, unlocktime=1700000000
                ),
            ]
        )

        result = sync_steam_achievements_for_user(
            user_id=user_with_steam.id,
            steam_client_fn=client,
        )

        # sample_unlockables crea 3 challenge_decks
        assert result.total_items_cascaded == len(sample_unlockables["challenges"])

    def test_completionist_plus_applies_gold_sticker_to_decks(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        client = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_30", achieved=True, unlocktime=1700000000
                ),
            ]
        )

        result = sync_steam_achievements_for_user(
            user_id=user_with_steam.id,
            steam_client_fn=client,
        )

        # sample_unlockables crea 2 decks → 2 USA con stake=8
        assert result.total_sticker_applications == len(sample_unlockables["decks"])

        usas = (
            db_session.query(UserStickerApplication)
            .filter_by(user_id=user_with_steam.id)
            .all()
        )
        assert all(u.highest_stake_order == 8 for u in usas)


# =============================================================================
# Idempotencia y sync delta
# =============================================================================


class TestIdempotency:
    """El segundo sync sin cambios no debe duplicar nada."""

    def test_repeated_sync_is_idempotent(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        client = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_01", achieved=True, unlocktime=1700000000
                ),
            ]
        )

        first = sync_steam_achievements_for_user(
            user_with_steam.id,
            steam_client_fn=client,
        )
        second = sync_steam_achievements_for_user(
            user_with_steam.id,
            steam_client_fn=client,
        )

        assert first.newly_unlocked_count == 1
        assert second.newly_unlocked_count == 0
        assert second.already_unlocked_count == 1
        assert second.total_items_cascaded == 0

        assert (
            db_session.query(UserAchievement)
            .filter_by(user_id=user_with_steam.id)
            .count()
        ) == 1
        assert (
            db_session.query(UserUnlock).filter_by(user_id=user_with_steam.id).count()
        ) == 1

    def test_delta_sync_only_processes_new_achievements(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        """Primer sync con 1 achievement; segundo con 2: solo procesa el nuevo."""
        client_v1 = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_01", achieved=True, unlocktime=1700000000
                ),
            ]
        )
        client_v2 = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_01", achieved=True, unlocktime=1700000000
                ),
                SteamAchievement(
                    apiname="BAL_23", achieved=True, unlocktime=1700100000
                ),
            ]
        )

        sync_steam_achievements_for_user(user_with_steam.id, steam_client_fn=client_v1)
        second = sync_steam_achievements_for_user(
            user_with_steam.id,
            steam_client_fn=client_v2,
        )

        # BAL_01 ya estaba; BAL_23 es nuevo y cascada los challenge_decks.
        assert second.newly_unlocked_count == 1
        assert second.already_unlocked_count == 1


# =============================================================================
# Apinames desconocidos y casos límite
# =============================================================================


class TestEdgeCases:

    def test_unknown_apinames_are_listed_not_raised(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
        sample_unlockables,
    ):
        """Si Steam devuelve un apiname no seedeado, va a unknown_apinames."""
        client = fake_steam_client(
            [
                SteamAchievement(
                    apiname="BAL_01", achieved=True, unlocktime=1700000000
                ),
                SteamAchievement(
                    apiname="BAL_99_NEW", achieved=True, unlocktime=1700100000
                ),
            ]
        )

        result = sync_steam_achievements_for_user(
            user_with_steam.id,
            steam_client_fn=client,
        )

        assert result.newly_unlocked_count == 1  # Solo BAL_01
        assert result.unknown_apinames == ["BAL_99_NEW"]

    def test_empty_steam_response_updates_last_sync(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
    ):
        """Aunque Steam no devuelva nada, last_steam_sync debe actualizarse."""
        assert user_with_steam.last_steam_sync is None

        client = fake_steam_client([])
        result = sync_steam_achievements_for_user(
            user_with_steam.id,
            steam_client_fn=client,
        )

        db_session.refresh(user_with_steam)
        assert user_with_steam.last_steam_sync is not None
        assert result.steam_achievements_received == 0
        assert result.newly_unlocked_count == 0
        assert result.unknown_apinames == []

    def test_last_steam_sync_matches_result_timestamp(
        self,
        db_session,
        user_with_steam,
        seeded_achievements,
    ):
        client = fake_steam_client([])
        result = sync_steam_achievements_for_user(
            user_with_steam.id,
            steam_client_fn=client,
        )

        db_session.refresh(user_with_steam)
        # Comparamos por timestamp (no por equality directa para evitar
        # problemas de timezone con SQLite).
        stored = user_with_steam.last_steam_sync
        if stored.tzinfo is None:
            # SQLite descartó la timezone; comparar componentes naive
            assert stored.replace(microsecond=0) == result.last_steam_sync_at.replace(
                tzinfo=None, microsecond=0
            )
        else:
            assert stored == result.last_steam_sync_at
