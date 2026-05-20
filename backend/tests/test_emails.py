"""Tests para el sistema de email (welcome + sync confirmation).

Estrategia: usamos `mail.record_messages()` de Flask-Mail para capturar
los Message objects que se "enviarían" sin que salgan realmente (en
TestConfig MAIL_SUPPRESS_SEND=True por defensa adicional).

Cobertura:
  - Wrapper send_email: captura mensaje correctamente, devuelve False
    si Mail falla.
  - Welcome email: se envía al crear user nuevo, NO al login subsiguiente,
    NO si no hay email, NO bloquea signup si Mail falla.
  - Sync confirmation: se envía si hay achievements nuevos, NO en
    re-sync idempotente, NO si no hay email, NO bloquea sync si Mail
    falla.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.api.auth import _get_or_create_user_from_firebase
from app.extensions import mail
from app.models import User
from app.services.achievement_sync import sync_steam_achievements_for_user
from app.services.email import send_email
from app.services.steam import SteamAchievement


# =============================================================================
# Wrapper bajo: send_email
# =============================================================================


class TestSendEmail:
    """Tests del wrapper send_email."""

    def test_records_message_when_suppress_send_is_true(self, app, db_session):
        """En TestConfig MAIL_SUPPRESS_SEND=True. El mensaje se captura
        en record_messages() pero no sale realmente al servidor SMTP."""
        with mail.record_messages() as outbox:
            ok = send_email(
                to="test@example.com",
                subject="Hello",
                html_body="<p>HTML body</p>",
                text_body="text body",
            )
        assert ok is True
        assert len(outbox) == 1
        msg = outbox[0]
        assert msg.subject == "Hello"
        assert msg.recipients == ["test@example.com"]
        assert "<p>HTML body</p>" in msg.html
        assert "text body" in msg.body

    def test_returns_false_when_mail_send_raises(self, app, db_session):
        """Si Mail levanta excepción internamente, send_email loguea y
        devuelve False en lugar de propagar."""
        with patch.object(mail, "send", side_effect=Exception("smtp down")):
            ok = send_email(
                to="test@example.com",
                subject="Hello",
                html_body="<p>x</p>",
            )
        assert ok is False


# =============================================================================
# Welcome email
# =============================================================================


class TestWelcomeEmail:
    """Tests del welcome email disparado al crear un user nuevo."""

    def test_sent_when_new_user_is_created(self, app, db_session):
        """User no existe en BD → se crea + se envía welcome."""
        decoded = {
            "uid": "fb-uid-new-user",
            "email": "newbie@example.com",
            "name": "New User",
            "picture": None,
        }
        with mail.record_messages() as outbox:
            user = _get_or_create_user_from_firebase(decoded)

        assert user.firebase_uid == "fb-uid-new-user"
        assert len(outbox) == 1
        msg = outbox[0]
        assert "Bienvenido" in msg.subject
        assert msg.recipients == ["newbie@example.com"]
        assert "New User" in msg.html
        assert "New User" in msg.body

    def test_not_sent_on_existing_user_login(
        self, app, db_session, sample_user
    ):
        """sample_user ya existe → al "loguearse" no se envía welcome
        (solo se sincronizan campos si cambiaron)."""
        decoded = {
            "uid": sample_user.firebase_uid,
            "email": sample_user.email,
            "name": sample_user.display_name,
            "picture": sample_user.avatar_url,
        }
        with mail.record_messages() as outbox:
            user = _get_or_create_user_from_firebase(decoded)

        assert user.id == sample_user.id
        assert len(outbox) == 0

    def test_not_sent_when_firebase_provides_no_email(self, app, db_session):
        """Algunos providers de Firebase (ej. anonymous) no incluyen email.
        En ese caso no intentamos enviar."""
        decoded = {
            "uid": "fb-uid-no-email",
            "email": None,
            "name": "No Email User",
            "picture": None,
        }
        with mail.record_messages() as outbox:
            user = _get_or_create_user_from_firebase(decoded)

        assert user.firebase_uid == "fb-uid-no-email"
        assert user.email is None
        assert len(outbox) == 0

    def test_mail_failure_does_not_abort_signup(self, app, db_session):
        """Si mail.send falla, el user sigue creándose. La excepción se
        captura dentro de send_email y no propaga al flujo de signup."""
        decoded = {
            "uid": "fb-uid-flaky-mail",
            "email": "test@example.com",
            "name": "Flaky Mail User",
            "picture": None,
        }
        with patch.object(mail, "send", side_effect=Exception("smtp down")):
            user = _get_or_create_user_from_firebase(decoded)

        # User persistido en BD a pesar del fallo de mail.
        assert user.id is not None
        assert user.firebase_uid == "fb-uid-flaky-mail"
        assert user.email == "test@example.com"


# =============================================================================
# Sync confirmation email
# =============================================================================


def _fake_steam_client(achievements: list[SteamAchievement]):
    """Construye un cliente Steam fake que ignora args y devuelve la
    lista dada. Idéntico al helper en test_achievement_sync_service.py."""
    def _client(steam_id, app_id=None, timeout=None):
        return achievements
    return _client


class TestSyncConfirmationEmail:
    """Tests del email de confirmación tras un sync de Steam."""

    @pytest.fixture
    def user_with_steam_and_email(self, db_session):
        """User con steam_id Y email vinculados, listo para sync con email."""
        user = User(
            firebase_uid="fb-sync-with-email",
            steam_id="76561198000000000",
            email="user@example.com",
            display_name="Tester",
        )
        db_session.add(user)
        db_session.commit()
        return user

    def test_sent_when_newly_unlocked_count_is_positive(
        self,
        app, db_session,
        user_with_steam_and_email,
        seeded_achievements,
    ):
        """Sync trae un achievement nuevo → email se envía con detalles."""
        client = _fake_steam_client([
            SteamAchievement(apiname="BAL_01", achieved=True, unlocktime=1700000000),
        ])

        with mail.record_messages() as outbox:
            result = sync_steam_achievements_for_user(
                user_id=user_with_steam_and_email.id,
                steam_client_fn=client,
            )

        assert result.newly_unlocked_count == 1
        assert len(outbox) == 1
        msg = outbox[0]
        assert "1 achievement" in msg.subject
        assert msg.recipients == ["user@example.com"]
        assert "Ante Up!" in msg.html

    def test_not_sent_on_idempotent_resync(
        self,
        app, db_session,
        user_with_steam_and_email,
        seeded_achievements,
    ):
        """Segundo sync sin cambios → newly_unlocked_count==0 → no email."""
        client = _fake_steam_client([
            SteamAchievement(apiname="BAL_01", achieved=True, unlocktime=1700000000),
        ])

        # Primer sync (consume el achievement)
        sync_steam_achievements_for_user(
            user_id=user_with_steam_and_email.id, steam_client_fn=client,
        )

        # Segundo sync con los mismos datos
        with mail.record_messages() as outbox:
            result = sync_steam_achievements_for_user(
                user_id=user_with_steam_and_email.id, steam_client_fn=client,
            )

        assert result.newly_unlocked_count == 0
        assert len(outbox) == 0

    def test_not_sent_when_user_has_no_email(
        self, app, db_session, seeded_achievements,
    ):
        """User sin email → no enviamos confirmation."""
        user_no_email = User(
            firebase_uid="fb-sync-no-email",
            steam_id="76561198000000001",
            display_name="NoEmail Tester",
        )
        db_session.add(user_no_email)
        db_session.commit()

        client = _fake_steam_client([
            SteamAchievement(apiname="BAL_01", achieved=True, unlocktime=1700000000),
        ])

        with mail.record_messages() as outbox:
            result = sync_steam_achievements_for_user(
                user_id=user_no_email.id, steam_client_fn=client,
            )

        assert result.newly_unlocked_count == 1
        assert len(outbox) == 0

    def test_mail_failure_does_not_abort_sync(
        self,
        app, db_session,
        user_with_steam_and_email,
        seeded_achievements,
    ):
        """Si mail.send falla, el sync sigue completándose y la BD se
        actualiza igual."""
        client = _fake_steam_client([
            SteamAchievement(apiname="BAL_01", achieved=True, unlocktime=1700000000),
        ])

        with patch.object(mail, "send", side_effect=Exception("smtp down")):
            result = sync_steam_achievements_for_user(
                user_id=user_with_steam_and_email.id,
                steam_client_fn=client,
            )

        # El sync completa con éxito a pesar del fallo de mail.
        assert result.newly_unlocked_count == 1
        db_session.refresh(user_with_steam_and_email)
        assert user_with_steam_and_email.last_steam_sync is not None