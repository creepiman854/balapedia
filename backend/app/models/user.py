"""Modelo User: usuario de Balapedia con autenticación dual Firebase/Steam."""
from datetime import datetime, timezone

from app.extensions import db


class User(db.Model):
    """Usuario registrado en la aplicación.

    Soporta tres flujos de autenticación que pueden convivir en un mismo registro:
      1. Solo Firebase (email/password o Google) -> firebase_uid presente.
      2. Solo Steam (OpenID 2.0)                  -> steam_id presente.
      3. Ambos vinculados                         -> firebase_uid Y steam_id presentes.

    El CheckConstraint garantiza que al menos uno de los dos identificadores
    esté presente, evitando usuarios "huérfanos" sin manera de iniciar sesión.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Identificadores externos (al menos uno obligatorio, ambos únicos)
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True, index=True)
    steam_id = db.Column(db.String(32), unique=True, nullable=True, index=True)

    # Datos de perfil (todos opcionales, dependen del proveedor de auth)
    email = db.Column(db.String(255), unique=True, nullable=True)
    display_name = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)

    # Metadatos de tracking
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_steam_sync = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relaciones inversas: un usuario tiene N progresos y N logros
    unlocks = db.relationship(
        "UserUnlock",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    achievements = db.relationship(
        "UserAchievement",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        db.CheckConstraint(
            "firebase_uid IS NOT NULL OR steam_id IS NOT NULL",
            name="ck_user_has_identity",
        ),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} display_name={self.display_name!r}>"