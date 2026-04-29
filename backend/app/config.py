import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 3,
        "pool_recycle": 280,        # recicla conexiones cada ~5 min para evitar timeouts
        "pool_pre_ping": True,      # detecta conexiones muertas antes de usarlas
    }
    STEAM_API_KEY = os.getenv("STEAM_API_KEY")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

class DevConfig(Config):
    DEBUG = True

class ProdConfig(Config):
    DEBUG = False