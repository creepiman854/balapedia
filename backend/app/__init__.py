from flask import Flask, jsonify
from .config import DevConfig
from .extensions import db, migrate, cors, limiter


def create_app(config_class=DevConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"])
    limiter.init_app(app)

    # Inicializa Firebase Admin SDK (auth verification)
    from app.extensions import init_firebase_admin
    init_firebase_admin(app)

    # Registra los modelos para que Flask-Migrate los descubra
    from app import models  # noqa: F401

    # Registra los comandos CLI personalizados (flask seed-db, flask steam-sync, ...)
    from app.cli import register_commands
    register_commands(app)

    # Registra los blueprints de la API
    from app.api.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.api.steam_auth import steam_auth_bp
    app.register_blueprint(steam_auth_bp)

    from app.api.steam_sync import steam_sync_bp
    app.register_blueprint(steam_sync_bp)
    
    # Endpoint de salud (verifica que el server arranca)
    @app.get("/api/health")
    def health():
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"
        status_code = 200 if db_status == "ok" else 503
        return (
            jsonify(
                service="balapedia-backend",
                status="ok" if db_status == "ok" else "degraded",
                database=db_status,
            ),
            status_code,
        )

    # Aquí se registrarán los blueprints más adelante:
    # from .api.auth import bp as auth_bp; app.register_blueprint(auth_bp)
    # from .api.jokers import bp as jokers_bp; app.register_blueprint(jokers_bp)

    return app
