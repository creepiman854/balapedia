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
    """Envía un email vía Flask-Mail.

    Args:
        to: dirección email del destinatario.
        subject: asunto.
        html_body: cuerpo HTML.
        text_body: cuerpo plano (fallback para clientes que no soportan
            HTML, mejor deliverability anti-spam). Si None, se omite.

    Returns:
        True si se envió correctamente; False si hubo excepción (logged).
    """
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
# Plantillas — funciones puras que devuelven (subject, html, text)
# =============================================================================


def render_welcome_email(
    display_name: Optional[str] = None,
) -> tuple[str, str, str]:
    """Construye el welcome email. Devuelve (subject, html, text)."""
    greeting = f"Hola {display_name}," if display_name else "¡Hola!"
    subject = "¡Bienvenido a Balapedia!"

    html = f"""\
<html>
  <body style="font-family: sans-serif; max-width: 600px; margin: auto;">
    <h1>¡Bienvenido a Balapedia!</h1>
    <p>{greeting}</p>
    <p>Gracias por crear tu cuenta en Balapedia, la wiki interactiva de
    Balatro.</p>
    <p>Desde tu perfil podrás:</p>
    <ul>
      <li>Vincular tu cuenta de Steam para sincronizar tu progreso
      automáticamente.</li>
      <li>Explorar el catálogo completo de Jokers, Decks, Achievements y
      más.</li>
      <li>Ver tu colección de Gold Stickers y tu avance hacia
      Completionist++.</li>
    </ul>
    <p>Ya puedes empezar.</p>
    <p style="color: #888; font-size: 0.85em;">
      Este es un email automático. No respondas a este mensaje.
    </p>
  </body>
</html>
"""

    text = f"""\
{greeting}

Gracias por crear tu cuenta en Balapedia.

Desde tu perfil podrás vincular tu cuenta de Steam para sincronizar tu
progreso, explorar el catálogo de Jokers/Decks/Achievements, y ver tu
colección de Gold Stickers.

¡Ya puedes empezar!

---
Este es un email automático. No respondas a este mensaje.
"""
    return subject, html, text


def render_sync_confirmation_email(
    display_name: Optional[str],
    newly_unlocked: list[dict],
    total_items_cascaded: int,
    total_sticker_applications: int,
) -> tuple[str, str, str]:
    """Construye el email de confirmación post-sync.

    Args:
        display_name: nombre del usuario para personalización.
        newly_unlocked: lista de dicts con info de cada achievement
            desbloqueado. Se espera al menos la clave `name`.
        total_items_cascaded: total de items desbloqueados via cascada.
        total_sticker_applications: total de Gold Stickers aplicados.
    """
    greeting = f"Hola {display_name}," if display_name else "¡Hola!"
    n = len(newly_unlocked)
    plural = "s" if n != 1 else ""
    subject = f"¡{n} achievement{plural} desbloqueado{plural} en Balapedia!"

    achievements_html = "\n".join(
        f"      <li>{ach.get('name', '?')}</li>" for ach in newly_unlocked
    )
    achievements_text = "\n".join(
        f"  - {ach.get('name', '?')}" for ach in newly_unlocked
    )

    html = f"""\
<html>
  <body style="font-family: sans-serif; max-width: 600px; margin: auto;">
    <h1>Sincronización con Steam completada</h1>
    <p>{greeting}</p>
    <p>Tu progreso de Balatro se ha sincronizado correctamente. Esto es
    lo nuevo:</p>

    <h2>{n} achievement{plural} desbloqueado{plural}</h2>
    <ul>
{achievements_html}
    </ul>

    <p>Adicionalmente:</p>
    <ul>
      <li><strong>{total_items_cascaded}</strong> items desbloqueados
      automáticamente en cascada.</li>
      <li><strong>{total_sticker_applications}</strong> Gold Stickers
      aplicados.</li>
    </ul>

    <p>Visita tu perfil para ver el detalle completo.</p>
    <p style="color: #888; font-size: 0.85em;">
      Este es un email automático. No respondas a este mensaje.
    </p>
  </body>
</html>
"""

    text = f"""\
{greeting}

Tu progreso de Balatro se ha sincronizado correctamente.

Achievements nuevos ({n}):
{achievements_text}

Adicionalmente:
  - {total_items_cascaded} items desbloqueados en cascada.
  - {total_sticker_applications} Gold Stickers aplicados.

Visita tu perfil para ver el detalle completo.

---
Este es un email automático. No respondas a este mensaje.
"""
    return subject, html, text


# =============================================================================
# API pública (la que invocan los hooks de signup y sync)
# =============================================================================


def send_welcome_email(to: str, display_name: Optional[str] = None) -> bool:
    """Envía el welcome email a un usuario recién creado.

    Failure no bloqueante: si Mail falla, logea y devuelve False sin
    propagar. El caller (auth.py) ignora el retorno para no abortar
    el signup.
    """
    subject, html, text = render_welcome_email(display_name)
    return send_email(to, subject, html, text)


def send_sync_confirmation_email(
    to: str,
    display_name: Optional[str],
    newly_unlocked: list[dict],
    total_items_cascaded: int,
    total_sticker_applications: int,
) -> bool:
    """Envía el email de confirmación tras un sync de Steam exitoso.

    Failure no bloqueante (igual que send_welcome_email).
    """
    subject, html, text = render_sync_confirmation_email(
        display_name=display_name,
        newly_unlocked=newly_unlocked,
        total_items_cascaded=total_items_cascaded,
        total_sticker_applications=total_sticker_applications,
    )
    return send_email(to, subject, html, text)
