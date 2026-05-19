"""Endpoints públicos del catálogo de Achievements.

  - GET /api/achievements        + /api/achievements/<id>

Incluye nested del unlock_factor enlazado (cuando existe) para que el
frontend pueda mostrar la condición humana del achievement sin un
round-trip extra.

Soporta filtrado por hidden y ordenamiento por steam_api_name. Sin
autenticación.
"""

from __future__ import annotations

from flask import Blueprint, jsonify
from sqlalchemy.orm import joinedload

from app.api._helpers import (
    apply_filters,
    apply_sort,
    paginate_query,
    parse_bool,
)
from app.api.schemas import AchievementSchema
from app.extensions import db
from app.models import Achievement

achievements_catalog_bp = Blueprint("catalog_achievements", __name__, url_prefix="/api")


_ACHIEVEMENT_FILTERS = {
    "hidden": parse_bool,
}

_ACHIEVEMENT_SORTS = {
    "id": Achievement.id,
    "steam_api_name": Achievement.steam_api_name,
    "name": Achievement.name,
}


def _not_found(resource: str, resource_id: int):
    """Respuesta 404 consistente con el resto de la API."""
    return (
        jsonify(error="not_found", message=f"{resource} {resource_id} not found"),
        404,
    )


@achievements_catalog_bp.route("/achievements", methods=["GET"])
def list_achievements():
    """Lista paginada de Achievements. Soporta ?hidden=true|false.

    Default sort por `steam_api_name` (BAL_01 → BAL_31), que coincide con
    el orden cronológico en que el desarrollador los añadió al juego —
    típicamente lo que el frontend quiere mostrar.
    """
    query = Achievement.query.options(joinedload(Achievement.unlock_factor))
    query = apply_filters(query, Achievement, _ACHIEVEMENT_FILTERS)
    query = apply_sort(query, _ACHIEVEMENT_SORTS, default_sort="steam_api_name")
    return jsonify(paginate_query(query, schema=AchievementSchema()))


@achievements_catalog_bp.route("/achievements/<int:achievement_id>", methods=["GET"])
def get_achievement(achievement_id: int):
    """Detalle de un Achievement por id."""
    achievement = db.session.get(Achievement, achievement_id)
    if achievement is None:
        return _not_found("Achievement", achievement_id)
    return jsonify(AchievementSchema().dump(achievement))
