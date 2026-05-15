"""Endpoints de vinculación de cuenta Steam vía OpenID 2.0.

Flujo:
  1. Usuario autenticado (Firebase) llama a /api/auth/steam/start.
     El backend genera un token firmado con su user_id y devuelve la
     URL de Steam OpenID donde redirigir.
  2. Frontend hace `window.location = steam_url`.
  3. Usuario inicia sesión en Steam, aprueba.
  4. Steam redirige al navegador a /api/auth/steam/callback con
     parámetros OpenID + el token firmado.
  5. Backend verifica el token, verifica los parámetros OpenID contra
     Steam (POST check_authentication), extrae el SteamID64, actualiza
     user.steam_id, y redirige al frontend con un indicador de éxito.

El token firmado entre /start y /callback se firma con SECRET_KEY del
proyecto e incluye un timestamp; expira en 10 minutos. Esto evita
necesidad de session cookies y mantiene el flujo stateless.
"""
import re
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, g, jsonify, redirect, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.api.auth import require_auth
from app.extensions import db
from app.models import User


steam_auth_bp = Blueprint("steam_auth", __name__, url_prefix="/api/auth/steam")

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
# Vida del link token (segundos): 10 minutos es suficiente para completar
# el flow de Steam sin dar margen excesivo a ataques de replay.
LINK_TOKEN_MAX_AGE = 600


def _serializer():
    """Devuelve un serializer firmado con SECRET_KEY del proyecto."""
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="steam-link",
    )


@steam_auth_bp.route("/start", methods=["GET"])
@require_auth
def start_steam_link():
    """Inicia el flow OpenID 2.0 de Steam.

    Requiere usuario autenticado (Firebase). Devuelve la URL de Steam a
    la que el frontend debe redirigir al navegador.
    """
    user: User = g.user

    # Token firmado con el user_id, embebido en la URL de retorno.
    link_token = _serializer().dumps(user.id)

    callback_url = (
        f"{current_app.config['PUBLIC_BACKEND_URL']}"
        f"/api/auth/steam/callback?link_token={link_token}"
    )

    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": callback_url,
        "openid.realm": current_app.config["PUBLIC_BACKEND_URL"],
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    redirect_url = f"{STEAM_OPENID_URL}?{urlencode(params)}"

    return jsonify(redirect_url=redirect_url)


@steam_auth_bp.route("/callback", methods=["GET"])
def steam_callback():
    """Callback al que Steam redirige tras la autenticación.

    Verifica el link_token (qué usuario está vinculando), valida los
    parámetros OpenID contra Steam mediante check_authentication, extrae
    el SteamID64, y actualiza el usuario en BD. Redirige al frontend con
    indicador de éxito o error.
    """
    frontend_url = current_app.config["PUBLIC_FRONTEND_URL"]
    redirect_to_profile = f"{frontend_url}/profile"

    # 1. Recupera el user_id del token firmado
    link_token = request.args.get("link_token")
    if not link_token:
        return redirect(f"{redirect_to_profile}?steam_link=missing_token")

    try:
        user_id = _serializer().loads(link_token, max_age=LINK_TOKEN_MAX_AGE)
    except SignatureExpired:
        return redirect(f"{redirect_to_profile}?steam_link=expired_token")
    except BadSignature:
        return redirect(f"{redirect_to_profile}?steam_link=invalid_token")

    user = User.query.get(user_id)
    if user is None:
        return redirect(f"{redirect_to_profile}?steam_link=user_not_found")

    # 2. Verifica los parámetros OpenID contra Steam
    verification_params = dict(request.args)
    verification_params.pop("link_token", None)
    verification_params["openid.mode"] = "check_authentication"

    try:
        response = requests.post(
            STEAM_OPENID_URL,
            data=verification_params,
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        current_app.logger.exception("Steam OpenID verification request failed")
        return redirect(f"{redirect_to_profile}?steam_link=verification_failed")

    if "is_valid:true" not in response.text:
        current_app.logger.warning(
            "Steam OpenID returned invalid claim for user %s: %s",
            user_id,
            response.text,
        )
        return redirect(f"{redirect_to_profile}?steam_link=invalid_claim")

    # 3. Extrae el SteamID64 del claimed_id
    # Formato: https://steamcommunity.com/openid/id/76561198XXXXXXX
    claimed_id = request.args.get("openid.claimed_id", "")
    match = re.search(r"/id/(\d+)$", claimed_id)
    if not match:
        current_app.logger.warning(
            "Could not extract SteamID from claimed_id: %s", claimed_id
        )
        return redirect(f"{redirect_to_profile}?steam_link=invalid_steam_id")

    steam_id = match.group(1)

    # 4. Verifica que ese SteamID no esté ya vinculado a otro user.
    existing = User.query.filter(
        User.steam_id == steam_id, User.id != user.id
    ).first()
    if existing:
        return redirect(f"{redirect_to_profile}?steam_link=already_linked")

    # 5. Actualiza el user y commit
    user.steam_id = steam_id
    db.session.commit()
    current_app.logger.info(
        "Linked Steam ID %s to user %s (firebase_uid=%s)",
        steam_id,
        user.id,
        user.firebase_uid,
    )

    return redirect(f"{redirect_to_profile}?steam_link=success")


@steam_auth_bp.route("/unlink", methods=["POST"])
@require_auth
def unlink_steam():
    """Desvincula la cuenta Steam del usuario autenticado.

    Requiere que el usuario tenga al menos firebase_uid presente
    (garantizado por el CheckConstraint del modelo User).
    """
    user: User = g.user
    if user.firebase_uid is None:
        # No tendría manera de loguearse después.
        return jsonify(error="Cannot unlink: would leave account without auth"), 400

    user.steam_id = None
    db.session.commit()
    return jsonify(message="Steam account unlinked successfully")