from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import DevConfig
from app.extensions import db, migrate, cors, limiter, mail


def create_app(config_class=DevConfig):
    app = Flask(__name__)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    app.config.from_object(config_class)

    # Extensiones
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )
    limiter.init_app(app)
    mail.init_app(app)

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

    # Blueprints del catálogo público (read-only, sin auth)
    from app.api.unlockables import unlockables_bp

    app.register_blueprint(unlockables_bp)

    from app.api.reference import reference_bp

    app.register_blueprint(reference_bp)

    from app.api.achievements import achievements_catalog_bp

    app.register_blueprint(achievements_catalog_bp)

    # Manejadores globales de errores (JSON consistente para 4xx/5xx)
    from app.api.errors import register_error_handlers

    register_error_handlers(app)

    from app.api.me import me_progress_bp

    app.register_blueprint(me_progress_bp)

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
