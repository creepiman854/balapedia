import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 3,
        "pool_recycle": 280,  # recicla conexiones cada ~5 min para evitar timeouts
        "pool_pre_ping": True,  # detecta conexiones muertas antes de usarlas
    }
    STEAM_API_KEY = os.getenv("STEAM_API_KEY")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    FIREBASE_ADMIN_CREDENTIALS_PATH = os.environ.get(
        "FIREBASE_ADMIN_CREDENTIALS_PATH", "./firebase-admin.json"
    )
    PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8080")
    PUBLIC_FRONTEND_URL = os.getenv("PUBLIC_FRONTEND_URL", "http://localhost:5173")


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False
