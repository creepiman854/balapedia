"""Servicio de envío de email transaccional vía Flask-Mail.

Wrapper sobre Flask-Mail que encapsula el envío SMTP. Las plantillas
HTML viven en este mismo archivo como funciones que devuelven la tupla
``(subject, html, text)`` — son lo bastante simples como para no
justificar archivos Jinja2 separados, y mantenerlas en código facilita
los tests y la trazabilidad.

Failure handling intencional: las funciones públicas
(``send_welcome_email``, ``send_sync_confirmation_email``) capturan
excepciones internamente y devuelven ``False`` + log warning, en lugar
de propagar. Razón: un fallo de SMTP nunca debe abortar el flujo
principal (signup, sync). Mejor que el usuario quede registrado sin
recibir el welcome a que el signup falle entero porque el servidor de
mail está caído.

En tests (TestConfig.MAIL_SUPPRESS_SEND=True) los envíos no salen
realmente; los mensajes se pueden capturar con
``mail.record_messages()``.
"""

from __future__ import annotations

import logging
from typing import Optional

from flask import current_app
from flask_mail import Message

from app.extensions import mail

logger = logging.getLogger(__name__)


# =============================================================================
# Envío bajo (wrapper sobre Flask-Mail)
# =============================================================================


def send_email(
    to: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Envía un email vía Flask-Mail."""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            html=html_body,
            body=text_body,
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception(
            "Failed to send email to %s with subject %r: %s",
            to,
            subject,
            e,
        )
        return False


# =============================================================================
# Plantillas — Alertas para el Administrador
# =============================================================================


def render_welcome_email(
    user_email: str,
    display_name: Optional[str] = None,
) -> tuple[str, str, str]:
    """Construye la alerta de nuevo registro para el admin."""
    name = display_name or "Sin nombre"
    subject = f"[ADMIN] Nuevo registro en Balapedia: {name}"

    html = f"""\
<html>
  <body style="font-family: sans-serif; max-width: 600px; margin: auto;">
    <h1 style="color: #2563eb;">Nuevo usuario registrado</h1>
    <p>Se ha registrado una nueva cuenta en Balapedia.</p>
    <ul>
      <li><strong>Nombre/Steam:</strong> {name}</li>
      <li><strong>Email:</strong> {user_email}</li>
    </ul>
    <p style="color: #888; font-size: 0.85em;">
      Alerta automática del sistema Balapedia.
    </p>
  </body>
</html>
"""

    text = f"""\
NUEVO USUARIO REGISTRADO

Se ha registrado una nueva cuenta en Balapedia.
- Nombre/Steam: {name}
- Email: {user_email}

---
Alerta automática del sistema Balapedia.
"""
    return subject, html, text


def render_sync_confirmation_email(
    user_email: str,
    display_name: Optional[str],
    newly_unlocked: list[dict],
    total_items_cascaded: int,
    total_sticker_applications: int,
) -> tuple[str, str, str]:
    """Construye la alerta de sincronización con novedades para el admin."""
    name = display_name or user_email
    n = len(newly_unlocked)
    plural = "s" if n != 1 else ""
    subject = f"[ADMIN] Sincronización de {name}: {n} logro{plural} nuevo{plural}"

    achievements_html = "\n".join(
        f"      <li>{ach.get('name', '?')}</li>" for ach in newly_unlocked
    )
    achievements_text = "\n".join(
        f"  - {ach.get('name', '?')}" for ach in newly_unlocked
    )

    html = f"""\
<html>
  <body style="font-family: sans-serif; max-width: 600px; margin: auto;">
    <h1 style="color: #059669;">Sincronización con novedades</h1>
    <p>El usuario <strong>{name}</strong> ({user_email}) acaba de sincronizar su progreso con éxito.</p>

    <h2>{n} achievement{plural} desbloqueado{plural}</h2>
    <ul>
{achievements_html}
    </ul>

    <p><strong>Efectos de la cascada:</strong></p>
    <ul>
      <li><strong>{total_items_cascaded}</strong> items base desbloqueados.</li>
      <li><strong>{total_sticker_applications}</strong> Gold Stickers aplicados.</li>
    </ul>

    <p style="color: #888; font-size: 0.85em;">
      Alerta automática del sistema Balapedia.
    </p>
  </body>
</html>
"""

    text = f"""\
SINCRONIZACIÓN CON NOVEDADES

El usuario {name} ({user_email}) acaba de sincronizar su progreso.

Achievements nuevos ({n}):
{achievements_text}

Efectos de la cascada:
  - {total_items_cascaded} items desbloqueados.
  - {total_sticker_applications} Gold Stickers aplicados.

---
Alerta automática del sistema Balapedia.
"""
    return subject, html, text


# =============================================================================
# API pública (la que invocan los hooks de signup y sync)
# =============================================================================


def _get_admin_email() -> str:
    """Extrae el email del admin desde la configuración MAIL_DEFAULT_SENDER."""
    sender = current_app.config.get("MAIL_DEFAULT_SENDER")
    # Flask-Mail permite que el sender sea un string o una tupla ("Nombre", "email")
    if isinstance(sender, tuple):
        return sender[1]
    return sender or "admin@localhost"


def send_welcome_email(to: str, display_name: Optional[str] = None) -> bool:
    """Envía la alerta de nuevo usuario al administrador.
    Nota: 'to' es el email del usuario registrado que nos llega desde el auth.
    """
    admin_email = _get_admin_email()

    subject, html, text = render_welcome_email(user_email=to, display_name=display_name)
    return send_email(admin_email, subject, html, text)


def send_sync_confirmation_email(
    to: str,
    display_name: Optional[str],
    newly_unlocked: list[dict],
    total_items_cascaded: int,
    total_sticker_applications: int,
) -> bool:
    """Envía la alerta de sincronización al administrador SOLO si hay novedades."""

    # GUARDIA DE FATIGA: Si no hay novedades, no enviamos correo y devolvemos True
    if (
        not newly_unlocked
        and total_items_cascaded == 0
        and total_sticker_applications == 0
    ):
        return True

    admin_email = _get_admin_email()

    subject, html, text = render_sync_confirmation_email(
        user_email=to,
        display_name=display_name,
        newly_unlocked=newly_unlocked,
        total_items_cascaded=total_items_cascaded,
        total_sticker_applications=total_sticker_applications,
    )
    return send_email(admin_email, subject, html, text)
