import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Reconecta si se cae.
        "pool_recycle": 299,  # Recicla la conexión cada 5 minutos.
        "pool_size": 5,  # Reduce el número de conexiones simultáneas.
        "max_overflow": 0,  # No desbordar la memoria.
    }
    STEAM_API_KEY = os.getenv("STEAM_API_KEY")
    STEAM_APP_ID = 2379780  # Balatro en Steam
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    FIREBASE_ADMIN_CREDENTIALS_PATH = os.environ.get(
        "FIREBASE_ADMIN_CREDENTIALS_PATH", "./firebase-admin.json"
    )
    PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8080")
    PUBLIC_FRONTEND_URL = os.getenv("PUBLIC_FRONTEND_URL", "http://localhost:5173")

    # Email (Flask-Mail)
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "2525"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in ("true", "1", "yes")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@balapedia.dev")


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
