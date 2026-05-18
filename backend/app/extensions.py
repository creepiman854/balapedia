import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])


def init_firebase_admin(app) -> bool:
    """Inicializa Firebase Admin SDK con las credenciales del archivo JSON.

    Idempotente: si ya está inicializado, no hace nada. Si falta el
    archivo de credenciales, NO falla pero loguea aviso y deja
    deshabilitada la verificación de tokens (útil para correr el backend
    en local sin Firebase configurado durante development inicial).

    Returns:
        True si Firebase Admin se inicializó correctamente.
        False si no había credenciales válidas (auth deshabilitada).
    """
    # Idempotencia: si ya hay app inicializada, salimos.
    if firebase_admin._apps:
        return True

    cred_path = app.config.get("FIREBASE_ADMIN_CREDENTIALS_PATH")
    if not cred_path:
        app.logger.warning(
            "FIREBASE_ADMIN_CREDENTIALS_PATH not set; auth endpoints "
            "will reject all requests."
        )
        return False

    # Resuelve rutas relativas respecto al directorio del backend
    if not os.path.isabs(cred_path):
        cred_path = os.path.join(app.root_path, "..", cred_path)
        cred_path = os.path.normpath(cred_path)

    if not os.path.exists(cred_path):
        app.logger.warning(
            "Firebase credentials file not found at %s; auth disabled.",
            cred_path,
        )
        return False

    try:
        cred = credentials.Certificate(cred_path)
        if not app.config.get("TESTING"):
            firebase_admin.initialize_app(cred)
        app.logger.info("Firebase Admin SDK initialized successfully.")
        return True
    except Exception as e:
        app.logger.error("Failed to initialize Firebase Admin: %s", e)
        return False
