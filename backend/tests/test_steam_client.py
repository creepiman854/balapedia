"""Tests del cliente HTTP de Steam (app/services/steam.py).

Mockea `requests.get` con `unittest.mock.patch` para evitar añadir
dependencias adicionales (responses, requests-mock). Cobertura:

  - Parseo correcto del payload happy path.
  - Mapeo de cada status HTTP a la excepción de dominio correspondiente.
  - Discriminación 401/403 vs perfil privado por el body de la respuesta.
  - Manejo de success=false en HTTP 200 (Steam usa este patrón a veces).
  - Timeout y errores de red.
  - JSON malformado.
  - Lista vacía de achievements (no error).
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from app.services.steam import (
    SteamApiError,
    SteamApiKeyInvalidError,
    SteamApiTimeoutError,
    SteamApiUnavailableError,
    SteamProfilePrivateError,
    SteamRateLimitError,
    get_player_achievements,
)

# =============================================================================
# Helpers
# =============================================================================


def _mock_response(status_code: int = 200, json_data=None, text: str = ""):
    """Construye un Mock que imita requests.Response."""
    response = Mock()
    response.status_code = status_code
    response.text = text
    if json_data is not None:
        response.json = Mock(return_value=json_data)
    else:
        response.json = Mock(side_effect=ValueError("not json"))
    return response


# =============================================================================
# Happy path y configuración
# =============================================================================


class TestHappyPath:
    """Casos en los que Steam responde correctamente."""

    def test_parses_normal_response(self, app):
        json_data = {
            "playerstats": {
                "steamID": "76561198000000000",
                "gameName": "Balatro",
                "achievements": [
                    {"apiname": "BAL_01", "achieved": 1, "unlocktime": 1700000000},
                    {"apiname": "BAL_02", "achieved": 0, "unlocktime": 0},
                    {"apiname": "BAL_03", "achieved": 1, "unlocktime": 1700100000},
                ],
                "success": True,
            }
        }
        with patch(
            "app.services.steam.requests.get",
            return_value=_mock_response(200, json_data=json_data),
        ):
            achievements = get_player_achievements("76561198000000000")

        assert len(achievements) == 3
        assert achievements[0].apiname == "BAL_01"
        assert achievements[0].achieved is True
        assert achievements[0].unlocktime == 1700000000
        assert achievements[1].achieved is False
        # unlocktime=0 se normaliza a None (achievement no desbloqueado).
        assert achievements[1].unlocktime is None

    def test_empty_achievements_list_is_not_an_error(self, app):
        json_data = {"playerstats": {"success": True, "achievements": []}}
        with patch(
            "app.services.steam.requests.get",
            return_value=_mock_response(200, json_data=json_data),
        ):
            result = get_player_achievements("76561198000000000")
        assert result == []

    def test_uses_steam_app_id_from_config_when_not_provided(self, app):
        json_data = {"playerstats": {"success": True, "achievements": []}}
        with patch(
            "app.services.steam.requests.get",
            return_value=_mock_response(200, json_data=json_data),
        ) as mock_get:
            get_player_achievements("76561198000000000")
            assert (
                mock_get.call_args.kwargs["params"]["appid"]
                == app.config["STEAM_APP_ID"]
            )

    def test_explicit_app_id_overrides_config(self, app):
        json_data = {"playerstats": {"success": True, "achievements": []}}
        with patch(
            "app.services.steam.requests.get",
            return_value=_mock_response(200, json_data=json_data),
        ) as mock_get:
            get_player_achievements("76561198000000000", app_id=999)
            assert mock_get.call_args.kwargs["params"]["appid"] == 999


# =============================================================================
# Errores HTTP traducidos a excepciones de dominio
# =============================================================================


class TestHttpErrorTranslation:
    """Verifica el mapeo de status codes a excepciones."""

    def test_401_without_private_indicator_raises_key_invalid(self, app):
        response = _mock_response(status_code=401, text="Unauthorized")
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamApiKeyInvalidError):
                get_player_achievements("76561198000000000")

    def test_403_with_private_profile_body_raises_private(self, app):
        response = _mock_response(
            status_code=403,
            text="The profile is not public.",
        )
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamProfilePrivateError):
                get_player_achievements("76561198000000000")

    def test_403_without_private_indicator_raises_key_invalid(self, app):
        """403 sin mensaje de 'private' es key issue, no perfil privado."""
        response = _mock_response(status_code=403, text="Forbidden")
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamApiKeyInvalidError):
                get_player_achievements("76561198000000000")

    def test_429_raises_rate_limit(self, app):
        response = _mock_response(status_code=429, text="Too many requests")
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamRateLimitError):
                get_player_achievements("76561198000000000")

    def test_500_raises_unavailable(self, app):
        response = _mock_response(status_code=500, text="Server error")
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamApiUnavailableError):
                get_player_achievements("76561198000000000")

    def test_503_raises_unavailable(self, app):
        response = _mock_response(status_code=503, text="Service unavailable")
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamApiUnavailableError):
                get_player_achievements("76561198000000000")

    def test_unexpected_status_raises_unavailable(self, app):
        response = _mock_response(status_code=418, text="I'm a teapot")
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamApiUnavailableError):
                get_player_achievements("76561198000000000")


# =============================================================================
# Errores de red y parsing
# =============================================================================


class TestNetworkAndParsingErrors:
    """Verifica el manejo de fallos de red y JSON malformado."""

    def test_timeout_raises_timeout_error(self, app):
        with patch(
            "app.services.steam.requests.get",
            side_effect=requests.Timeout("read timed out"),
        ):
            with pytest.raises(SteamApiTimeoutError):
                get_player_achievements("76561198000000000")

    def test_connection_error_raises_unavailable(self, app):
        with patch(
            "app.services.steam.requests.get",
            side_effect=requests.ConnectionError("no route"),
        ):
            with pytest.raises(SteamApiUnavailableError):
                get_player_achievements("76561198000000000")

    def test_malformed_json_raises_unavailable(self, app):
        response = _mock_response(status_code=200, json_data=None, text="not json")
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamApiUnavailableError, match="malformed JSON"):
                get_player_achievements("76561198000000000")


# =============================================================================
# success=false con HTTP 200 (caso peculiar de Steam)
# =============================================================================


class TestSuccessFalseInBody:
    """Steam a veces devuelve 200 OK con success=false en el body."""

    def test_success_false_with_private_message_raises_private(self, app):
        json_data = {
            "playerstats": {
                "success": False,
                "error": "Profile is not public",
            }
        }
        response = _mock_response(status_code=200, json_data=json_data)
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamProfilePrivateError):
                get_player_achievements("76561198000000000")

    def test_success_false_with_other_error_raises_generic(self, app):
        json_data = {
            "playerstats": {
                "success": False,
                "error": "Invalid SteamID",
            }
        }
        response = _mock_response(status_code=200, json_data=json_data)
        with patch("app.services.steam.requests.get", return_value=response):
            with pytest.raises(SteamApiError):
                get_player_achievements("76561198000000000")


# =============================================================================
# Configuración del backend
# =============================================================================


class TestBackendConfig:
    """Errores de configuración del propio backend."""

    def test_missing_steam_api_key_raises_key_invalid(self, app):
        # Sobreescribe temporalmente el config para simular key ausente.
        original = app.config.get("STEAM_API_KEY")
        app.config["STEAM_API_KEY"] = None
        try:
            with pytest.raises(SteamApiKeyInvalidError, match="not configured"):
                get_player_achievements("76561198000000000")
        finally:
            app.config["STEAM_API_KEY"] = original
