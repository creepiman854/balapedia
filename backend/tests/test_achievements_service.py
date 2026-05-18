"""Tests del servicio app/services/achievements.py.

Cubre los tres caminos del módulo:
  1. Cascada genérica por shared unlock_factor (Ante Up! → Showman).
  2. Idempotencia + variantes de la API pública (by_id y by_code).
  3. Los 4 resolvers especiales: Rule Breaker, Completionist,
     Completionist+ y Completionist++.

Ubicación: tests/test_achievements_service.py
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models import (
    UserAchievement,
    UserStickerApplication,
    UserUnlock,
)
from app.models.enums import UnlockSource
from app.services.achievements import (
    unlock_achievement_by_code,
    unlock_achievement_for_user,
)


# =============================================================================
# Cascada genérica + idempotencia + API pública
# =============================================================================


class TestGenericFlow:
    """Tests del flujo común a todos los achievements."""

    def test_shared_factor_cascades_to_linked_unlockable(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        """Ante Up! (factor REACH_ANTE_4) debe desbloquear Showman también."""
        ante_up = seeded_achievements["achievements"]["BAL_01"]

        result = unlock_achievement_for_user(
            user_id=sample_user.id,
            achievement_id=ante_up.id,
        )

        assert result.achievement_was_already_unlocked is False
        assert len(result.cascaded_unlockables) == 1
        assert result.cascaded_unlockables[0].name == "Showman"

        # Verificación en BD: UserAchievement marcado
        ua = (db_session.query(UserAchievement)
              .filter_by(user_id=sample_user.id, achievement_id=ante_up.id)
              .one())
        assert ua.unlocked is True
        assert ua.unlocked_at is not None

        # Verificación en BD: UserUnlock para Showman creado
        showman = sample_unlockables["showman"]
        uu = (db_session.query(UserUnlock)
              .filter_by(user_id=sample_user.id, unlockable_id=showman.id)
              .one())
        assert uu.unlocked is True

    def test_is_idempotent_on_second_call(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        """Llamar dos veces no duplica filas ni reaplica cascadas."""
        ante_up = seeded_achievements["achievements"]["BAL_01"]

        first = unlock_achievement_for_user(sample_user.id, ante_up.id)
        second = unlock_achievement_for_user(sample_user.id, ante_up.id)

        assert first.achievement_was_already_unlocked is False
        assert second.achievement_was_already_unlocked is True
        assert len(second.cascaded_unlockables) == 0

        showman = sample_unlockables["showman"]
        count = (db_session.query(UserUnlock)
                 .filter_by(user_id=sample_user.id, unlockable_id=showman.id)
                 .count())
        assert count == 1, "No deben crearse UserUnlock duplicados"

    def test_by_code_works_same_as_by_id(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        """La variante by_code debe producir el mismo efecto que by_id."""
        result = unlock_achievement_by_code(
            user_id=sample_user.id,
            steam_api_name="BAL_01",
        )

        assert result.achievement.steam_api_name == "BAL_01"
        assert len(result.cascaded_unlockables) == 1
        assert result.cascaded_unlockables[0].name == "Showman"

    def test_by_id_with_nonexistent_id_raises(
        self, db_session, sample_user, seeded_achievements
    ):
        with pytest.raises(ValueError, match="no encontrado"):
            unlock_achievement_for_user(sample_user.id, achievement_id=999_999)

    def test_by_code_with_nonexistent_name_raises(
        self, db_session, sample_user, seeded_achievements
    ):
        with pytest.raises(ValueError, match="no encontrado"):
            unlock_achievement_by_code(sample_user.id, steam_api_name="BAL_DOES_NOT_EXIST")


# =============================================================================
# Resolvers especiales
# =============================================================================


class TestRuleBreaker:
    """BAL_23 Rule Breaker → desbloquea todos los challenge decks."""

    def test_cascades_to_all_challenge_decks(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        rule_breaker = seeded_achievements["achievements"]["BAL_23"]
        challenges = sample_unlockables["challenges"]

        result = unlock_achievement_for_user(sample_user.id, rule_breaker.id)

        assert len(result.cascaded_unlockables) == len(challenges)

        unlocked_ids = {
            uu.unlockable_id
            for uu in db_session.query(UserUnlock).filter_by(user_id=sample_user.id).all()
        }
        for ch in challenges:
            assert ch.id in unlocked_ids

    def test_is_idempotent(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        rule_breaker = seeded_achievements["achievements"]["BAL_23"]

        unlock_achievement_for_user(sample_user.id, rule_breaker.id)
        second = unlock_achievement_for_user(sample_user.id, rule_breaker.id)

        assert second.achievement_was_already_unlocked is True
        assert len(second.cascaded_unlockables) == 0


class TestCompletionist:
    """BAL_29 Completionist → desbloquea todos los unlockables con factor."""

    def test_cascades_only_to_items_with_factor(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        """En el fixture solo Showman tiene unlock_factor; los demás NULL."""
        completionist = seeded_achievements["achievements"]["BAL_29"]

        result = unlock_achievement_for_user(sample_user.id, completionist.id)

        assert len(result.cascaded_unlockables) == 1
        assert result.cascaded_unlockables[0].name == "Showman"

        # base_joker, decks y challenges NO deben aparecer
        unlocked_ids = {
            uu.unlockable_id
            for uu in db_session.query(UserUnlock).filter_by(user_id=sample_user.id).all()
        }
        assert sample_unlockables["base_joker"].id not in unlocked_ids
        for deck in sample_unlockables["decks"]:
            assert deck.id not in unlocked_ids
        for ch in sample_unlockables["challenges"]:
            assert ch.id not in unlocked_ids


class TestCompletionistPlus:
    """BAL_30 Completionist+ → Gold Sticker (stake=8) en todos los decks."""

    def test_applies_gold_sticker_to_all_decks(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        cp = seeded_achievements["achievements"]["BAL_30"]
        decks = sample_unlockables["decks"]

        result = unlock_achievement_for_user(sample_user.id, cp.id)

        assert len(result.cascaded_sticker_applications) == len(decks)

        usas = (db_session.query(UserStickerApplication)
                .filter_by(user_id=sample_user.id)
                .all())
        assert len(usas) == len(decks)
        assert all(u.highest_stake_order == 8 for u in usas)
        sticker_ids = {u.unlockable_id for u in usas}
        for deck in decks:
            assert deck.id in sticker_ids

    def test_does_not_apply_sticker_to_jokers_or_challenges(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        """Solo decks, no debe tocar jokers ni challenge_decks."""
        cp = seeded_achievements["achievements"]["BAL_30"]

        unlock_achievement_for_user(sample_user.id, cp.id)

        sticker_ids = {
            u.unlockable_id
            for u in db_session.query(UserStickerApplication).all()
        }
        for joker in sample_unlockables["jokers"]:
            assert joker.id not in sticker_ids
        for ch in sample_unlockables["challenges"]:
            assert ch.id not in sticker_ids

    def test_promotes_existing_sticker_to_gold(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        """Una USA preexistente en stake=3 debe promoverse a stake=8."""
        deck = sample_unlockables["decks"][0]
        pre = UserStickerApplication(
            user_id=sample_user.id,
            unlockable=deck,
            highest_stake_order=3,
            source=UnlockSource.MANUAL,
            earned_at=datetime.now(timezone.utc),
        )
        db_session.add(pre)
        db_session.commit()

        cp = seeded_achievements["achievements"]["BAL_30"]
        unlock_achievement_for_user(sample_user.id, cp.id)

        promoted = (db_session.query(UserStickerApplication)
                    .filter_by(user_id=sample_user.id, unlockable_id=deck.id)
                    .one())
        assert promoted.highest_stake_order == 8

    def test_does_not_demote_higher_sticker(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        """Si ya está en stake=8, no debe degradarse ni duplicarse."""
        deck = sample_unlockables["decks"][0]
        existing = UserStickerApplication(
            user_id=sample_user.id,
            unlockable=deck,
            highest_stake_order=8,
            source=UnlockSource.STEAM_SYNC,
            earned_at=datetime.now(timezone.utc),
        )
        db_session.add(existing)
        db_session.commit()

        cp = seeded_achievements["achievements"]["BAL_30"]
        unlock_achievement_for_user(sample_user.id, cp.id)

        count = (db_session.query(UserStickerApplication)
                 .filter_by(user_id=sample_user.id, unlockable_id=deck.id)
                 .count())
        assert count == 1, "Debe haber una sola USA, no duplicada"


class TestCompletionistPlusPlus:
    """BAL_31 Completionist++ → Gold Sticker (stake=8) en todos los jokers."""

    def test_applies_gold_sticker_to_all_jokers(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        cpp = seeded_achievements["achievements"]["BAL_31"]
        jokers = sample_unlockables["jokers"]

        result = unlock_achievement_for_user(sample_user.id, cpp.id)

        assert len(result.cascaded_sticker_applications) == len(jokers)

        usas = (db_session.query(UserStickerApplication)
                .filter_by(user_id=sample_user.id)
                .all())
        assert len(usas) == len(jokers)
        assert all(u.highest_stake_order == 8 for u in usas)
        sticker_ids = {u.unlockable_id for u in usas}
        for joker in jokers:
            assert joker.id in sticker_ids

    def test_does_not_apply_sticker_to_decks(
        self, db_session, sample_user, seeded_achievements, sample_unlockables
    ):
        cpp = seeded_achievements["achievements"]["BAL_31"]

        unlock_achievement_for_user(sample_user.id, cpp.id)

        sticker_ids = {
            u.unlockable_id
            for u in db_session.query(UserStickerApplication).all()
        }
        for deck in sample_unlockables["decks"]:
            assert deck.id not in sticker_ids
