"""Manejadores globales de errores para la API.

Convierten cualquier excepción no atrapada por un endpoint en una
respuesta JSON consistente con la forma::

    {
      "error": "<código>",
      "message": "<mensaje legible>",
      "details": <objeto opcional con info adicional>
    }

Beneficios:
  - El frontend nunca recibe HTML inesperado (que rompería un fetch
    esperando JSON).
  - Los códigos de error son strings estables, fáciles de discriminar
    desde el cliente sin parsear mensajes.
  - Errores no controlados se logean automáticamente para diagnóstico
    sin filtrar detalles internos al usuario.

Se registran en `create_app()` llamando a `register_error_handlers(app)`.
"""
from __future__ import annotations

from flask import Flask, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    """Registra los handlers de errores en la app.

    Orden de resolución (Flask los aplica de más específico a más general):
      1. ValidationError de marshmallow → 400 con `details` por campo.
      2. HTTPException (404, 405, 400, etc.) → JSON con código y mensaje.
      3. Exception → 500 logeado, mensaje genérico al cliente (no expone
         stack ni detalles internos).
    """

    @app.errorhandler(ValidationError)
    def _handle_validation_error(err: ValidationError):
        """Errores de validación de marshmallow (filtros/sort/paginación)."""
        return (
            jsonify(
                error="validation_error",
                message="Invalid request parameters",
                details=err.messages,
            ),
            400,
        )

    @app.errorhandler(HTTPException)
    def _handle_http_exception(err: HTTPException):
        """Cualquier HTTPException de werkzeug (404, 405, etc.) se traduce
        a JSON con código snake_case del nombre y el mensaje original."""
        error_code = (err.name or "http_error").lower().replace(" ", "_")
        return (
            jsonify(
                error=error_code,
                message=err.description or "An HTTP error occurred",
            ),
            err.code or 500,
        )

    @app.errorhandler(Exception)
    def _handle_unexpected_exception(err: Exception):
        """Catch-all para excepciones no controladas. Se logea el stack
        completo y se devuelve un 500 genérico al cliente (sin filtrar
        internals)."""
        app.logger.exception("Unhandled exception in request handler")
        return (
            jsonify(
                error="internal_server_error",
                message="An unexpected error occurred",
            ),
            500,
        )