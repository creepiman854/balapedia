"""Helpers compartidos por los endpoints del catálogo.

Tres responsabilidades:
  1. **Paginación**: parsea `?page=&per_page=` con defaults razonables y
     límites para evitar que un cliente pida 100k filas y tumbe el server.
  2. **Filtrado**: aplica filtros de query params validados contra una
     whitelist. Sin whitelist el cliente podría filtrar por columnas
     sensibles o causar errores que filtren información del esquema.
  3. **Sorting**: aplica `order_by` validado también contra whitelist,
     con sintaxis `?sort=campo` (asc) o `?sort=-campo` (desc).

Defensa contra SQL injection: ningún nombre de columna se interpola
desde input del cliente. Todo va vía whitelist explícita de columnas
SQLAlchemy ya bindeadas en el modelo.
"""

from __future__ import annotations

import enum
from typing import Any, Callable

from flask import request
from marshmallow import ValidationError
from sqlalchemy.orm.query import Query

# Defaults sensatos. MAX_PER_PAGE evita que un cliente pida 1M filas.
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


# =============================================================================
# Paginación
# =============================================================================


def parse_pagination_params() -> tuple[int, int]:
    """Lee y valida `?page=N&per_page=M` desde `request.args`.

    Returns:
        Tupla (page, per_page).

    Raises:
        ValidationError si los valores no son enteros o están fuera de
        rango. El handler global la traduce a HTTP 400 con detalle del
        campo inválido.
    """
    try:
        page = int(request.args.get("page", DEFAULT_PAGE))
        per_page = int(request.args.get("per_page", DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        raise ValidationError({"pagination": "page and per_page must be integers"})

    if page < 1:
        raise ValidationError({"page": "must be >= 1"})
    if per_page < 1 or per_page > MAX_PER_PAGE:
        raise ValidationError({"per_page": f"must be between 1 and {MAX_PER_PAGE}"})

    return page, per_page


def paginate_query(query: Query, schema=None) -> dict[str, Any]:
    """Aplica paginación a una query SQLAlchemy y devuelve dict JSON-ready.

    Args:
        query: SQLAlchemy Query a paginar (ya con sus filtros y order_by
            aplicados antes de llamar aquí).
        schema: marshmallow Schema opcional. Si se provee, serializa los
            items con `schema.dump(items, many=True)`. Si es None, devuelve
            los objetos sin serializar (útil para tests).

    Returns:
        Dict con keys:
          - `items`: lista (serializada o no según schema).
          - `page`, `per_page`: parámetros usados.
          - `total`: total de filas que cumplen filtros, sin paginar.
          - `total_pages`: división con redondeo arriba.
    """
    page, per_page = parse_pagination_params()

    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()

    if schema is not None:
        items_data = schema.dump(items, many=True)
    else:
        items_data = items

    total_pages = (total + per_page - 1) // per_page if total > 0 else 0

    return {
        "items": items_data,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }


# =============================================================================
# Filtrado
# =============================================================================


def apply_filters(
    query: Query,
    model: Any,
    allowed_filters: dict[str, Callable[[str], Any]],
) -> Query:
    """Aplica filtros de query params validados contra una whitelist.

    Cada filtro permitido se mapea a un constructor que convierte el valor
    de string a un tipo concreto (int, bool, enum). Si el cliente envía
    `?rarity=COMMON`, busca `'rarity'` en `allowed_filters`, llama a
    `JokerRarity('COMMON')` para validar, y añade
    `query.filter(Joker.rarity == JokerRarity.COMMON)`.

    Defensa contra SQL injection: solo los campos en `allowed_filters` se
    aceptan; cualquier otro query param se ignora silenciosamente. La
    conversión de tipo valida formato y rechaza inputs maliciosos.

    Args:
        query: Query base.
        model: Clase del modelo SQLAlchemy. Sus columnas se accesan via
            `getattr(model, param_name)`.
        allowed_filters: Dict `{param_name: type_constructor}`.
            Ej. `{"rarity": JokerRarity, "in_shop": _parse_bool}`.

    Returns:
        Query con los filtros añadidos.

    Raises:
        ValidationError si un valor recibido no se puede convertir al tipo
        esperado.
    """
    for param_name, type_constructor in allowed_filters.items():
        if param_name not in request.args:
            continue
        raw_value = request.args.get(param_name)
        try:
            # Para Enums hacemos lookup por NAME (UPPERCASE), consistente con
            # cómo marshmallow los serializa por defecto y con cómo MySQL
            # los almacena. Para constructores normales (int, bool, str)
            # llamamos el constructor con el valor crudo.
            if isinstance(type_constructor, type) and issubclass(
                type_constructor, enum.Enum
            ):
                value = type_constructor[raw_value]
            else:
                value = type_constructor(raw_value)
        except (ValueError, KeyError) as e:
            raise ValidationError({param_name: f"invalid value: {raw_value!r} ({e})"})
        column = getattr(model, param_name)
        query = query.filter(column == value)
    return query


def parse_bool(raw: str) -> bool:
    """Convierte strings comunes a bool. Útil como type_constructor en
    `allowed_filters`."""
    lowered = raw.strip().lower()
    if lowered in ("1", "true", "yes", "y"):
        return True
    if lowered in ("0", "false", "no", "n"):
        return False
    raise ValueError(f"cannot parse {raw!r} as bool")


# =============================================================================
# Sorting
# =============================================================================


def apply_sort(
    query: Query,
    allowed_sorts: dict[str, Any],
    default_sort: str,
) -> Query:
    """Aplica ordenamiento via `?sort=field` (asc) o `?sort=-field` (desc).

    Defensa: solo nombres en `allowed_sorts` se aceptan. Esto evita que un
    cliente intente ordenar por columnas no expuestas en la API (ej. una
    columna de timestamp interno), lo cual además podría filtrar
    información estructural del esquema via mensajes de error.

    Args:
        query: Query base.
        allowed_sorts: Dict `{sort_name: column}` con las columnas
            permitidas. La key es el nombre visible al cliente (puede
            diferir del nombre real de la columna).
        default_sort: Nombre del sort por defecto si el cliente no
            especifica uno.

    Returns:
        Query con `order_by` aplicado.

    Raises:
        ValidationError si el sort solicitado no está en la whitelist.
    """
    sort_param = request.args.get("sort", default_sort)
    descending = sort_param.startswith("-")
    field_name = sort_param.lstrip("-")

    if field_name not in allowed_sorts:
        raise ValidationError(
            {
                "sort": (
                    f"invalid sort field: {field_name!r}; "
                    f"allowed: {sorted(allowed_sorts.keys())}"
                )
            }
        )

    column = allowed_sorts[field_name]
    if descending:
        column = column.desc()
    return query.order_by(column)
