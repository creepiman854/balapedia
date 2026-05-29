"""Endpoints de autenticación y autorización.

Modelo: el frontend autentica al usuario contra Firebase (vía Firebase JS
SDK) y obtiene un ID Token. Cada petición a la API protegida envía ese
token en el header ``Authorization: Bearer <token>``. El decorador
``@require_auth`` lo verifica con firebase-admin (server-side) y, si es
válido, busca o crea el usuario correspondiente en la BD.

La autenticación dual (Firebase + Steam) se materializa en el modelo
``User`` que ya tiene campos ``firebase_uid`` y ``steam_id`` nullable.
Esta rama solo cubre la parte Firebase; la Steam se añadirá en una rama
posterior.
"""

from functools import wraps
from typing import Optional

from firebase_admin import auth as firebase_auth
from flask import Blueprint, current_app, g, jsonify, request

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User

from app.services.email import send_welcome_email

auth_bp = Blueprint("auth", __name__, url_prefix="/api")


def require_auth(f):
    """Decorador que verifica un ID Token de Firebase del header
    ``Authorization`` y attach el ``User`` correspondiente a ``g.user``.

    Comportamiento:
      - Si falta el header o no empieza por "Bearer ", devuelve 401.
      - Si el token no verifica (firmado mal, expirado, etc.), devuelve 401.
      - Si verifica pero el usuario no existe en BD, lo crea
        automáticamente con los datos del token (email, name, picture).
      - Si verifica y el usuario existe, sincroniza email/name/picture
        si han cambiado en Firebase.

    El handler decorado puede acceder al usuario autenticado vía
    ``flask.g.user``.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify(error="Missing or invalid Authorization header"), 401

        token = auth_header[len("Bearer ") :].strip()
        if not token:
            return jsonify(error="Empty bearer token"), 401

        try:
            decoded = firebase_auth.verify_id_token(token)
        except firebase_auth.ExpiredIdTokenError:
            return jsonify(error="Token expired"), 401
        except firebase_auth.RevokedIdTokenError:
            return jsonify(error="Token revoked"), 401
        except firebase_auth.InvalidIdTokenError:
            return jsonify(error="Invalid token"), 401
        except ValueError as e:
            # firebase_auth puede lanzar ValueError si el SDK no está
            # inicializado (caso del backend corriendo sin credenciales).
            current_app.logger.error("Firebase verification error: %s", e)
            return jsonify(error="Auth service unavailable"), 503
        except Exception as e:
            current_app.logger.exception("Unexpected auth error")
            return jsonify(error=f"Auth error: {e}"), 401

        # Token válido: busca o crea el usuario.
        user = _get_or_create_user_from_firebase(decoded)
        g.user = user

        return f(*args, **kwargs)

    return wrapper


def _get_or_create_user_from_firebase(decoded: dict) -> User:
    """Busca el User por firebase_uid; si no existe, lo crea.

    Si existe, sincroniza email/display_name/avatar si han cambiado en
    Firebase (p.ej. el usuario actualizó su nombre en Google).
    """
    firebase_uid = decoded["uid"]
    email: Optional[str] = decoded.get("email")
    name: Optional[str] = decoded.get("name")
    picture: Optional[str] = decoded.get("picture")

    user = User.query.filter_by(firebase_uid=firebase_uid).first()

    if user is None:
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            display_name=name,
            avatar_url=picture,
        )
        db.session.add(user)

        try:
            db.session.commit()
            # FÍJATE AQUÍ: Hemos quitado el "return user"
            # Si tiene éxito, simplemente sigue hacia abajo para mandar el email
        except IntegrityError:
            # Condición de carrera: otra petición paralela creó a este usuario
            # en el milisegundo exacto en el que estábamos intentando hacerlo.
            # Deshacemos nuestra transacción y obtenemos el usuario que ya se guardó.
            db.session.rollback()
            return User.query.filter_by(firebase_uid=firebase_uid).one()

        current_app.logger.info(
            "Created new user (firebase_uid=%s, email=%s)",
            firebase_uid,
            email,
        )
        # Welcome email best-effort: solo si Firebase nos dio email
        # (algunos providers como Steam-via-Firebase no lo incluyen).
        # send_welcome_email captura excepciones internamente: si Mail
        # falla, logea y devuelve False sin abortar el signup.
        if email:
            send_welcome_email(to=email, display_name=name)
    else:
        # Sincroniza campos opcionales si cambiaron
        changed = False
        if email and user.email != email:
            user.email = email
            changed = True
        if name and user.display_name != name:
            user.display_name = name
            changed = True
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            changed = True
        if changed:
            db.session.commit()

    return user


# ──────────────────────────────────────────────────────────────────────
#  Endpoints
# ──────────────────────────────────────────────────────────────────────


@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_me():
    """Devuelve el perfil del usuario autenticado.

    El frontend lo llama después de cada login para confirmar la sesión
    y obtener los datos de perfil (id interno, email, avatar, etc.).
    """
    user: User = g.user
    return jsonify(
        id=user.id,
        firebase_uid=user.firebase_uid,
        steam_id=user.steam_id,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_steam_sync=(
            user.last_steam_sync.isoformat() if user.last_steam_sync else None
        ),
    )


@auth_bp.route("/delete-account", methods=["DELETE"])
@require_auth
def delete_account():
    """Elimina completamente el usuario:
    - Firebase Auth (login)
    - Base de datos (progreso Balapedia)
    """

    user: User = g.user
    firebase_uid = user.firebase_uid

    current_app.logger.warning(
        "FULL DELETE user_id=%s firebase_uid=%s steam_id=%s",
        user.id,
        user.firebase_uid,
        user.steam_id,
    )

    # Borra usuario de Firebase Auth (email/google login)
    if firebase_uid:
        try:
            firebase_auth.delete_user(firebase_uid)
        except firebase_auth.UserNotFoundError:
            current_app.logger.warning(
                "Firebase user not found while deleting: %s",
                firebase_uid,
            )
        except Exception as e:
            current_app.logger.exception("Failed to delete Firebase user: %s", e)
            return (
                jsonify(
                    error="firebase_delete_failed",
                    message="The authentication account could not be deleted.",
                ),
                500,
            )

    # Borra usuario de tu BD (Steam + progreso)
    db.session.delete(user)
    db.session.commit()

    current_app.logger.warning("User deleted from DB: user_id=%s", user.id)

    return jsonify(message="Account fully deleted"), 200
