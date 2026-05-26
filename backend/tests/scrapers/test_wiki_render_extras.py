"""Tests adicionales para `app.scrapers.wiki.render_wikitext`.

Estos tests cubren los dos bugs cerrados en `fix/seed-wikitext-cleanup`:

1. `arg(n)` ahora es recursivo — plantillas anidadas dentro de los
   args de otras plantillas se aplanan en lugar de salir como
   wikitext literal.

2. La familia "color-discard" ahora incluye `c` y aliases además
   de `hl`. Antes `{{c|red|+50 Mult}}` devolvía el color en lugar
   del texto.

Diseño: cada test consume un fixture mínimo (no carga la wiki
entera, solo el fragmento de wikitexto que ejercita el caso). Si
falla, el output es trivial de diagnosticar — el fragmento mismo
del fixture es la documentación del caso.

"""
from __future__ import annotations

import pytest

from app.scrapers.wiki import render_wikitext


# =============================================================================
# Bug A: `{{c|...}}` y aliases color-discard
# =============================================================================


class TestColorDiscardTemplates:
    """Familia de plantillas que descartan arg(1)=color y devuelven arg(2)."""

    def test_c_template_discards_color_returns_text(self):
        """Caso reportado por el usuario: `{{c|red|+50 Mult}}` debe
        devolver '+50 Mult', no 'red'.

        Antes del fix, el parser caía al unknown branch y devolvía
        `arg(1)` que es el color. Tras añadir 'c' a la whitelist
        color-discard, devuelve `arg(2)` que es el texto."""
        assert render_wikitext("{{c|red|+50 Mult}}") == "+50 Mult"

    def test_hl_template_still_works(self):
        """Regresión: el handler de `hl` ya existía y debe seguir
        funcionando igual."""
        assert render_wikitext("{{hl|orange|Tarot}}") == "Tarot"

    @pytest.mark.parametrize(
        "alias",
        ["color", "fc", "clr", "textcolor"],
    )
    def test_color_discard_aliases(self, alias):
        """Aliases de color-discard documentados en la docstring.
        Probables apariciones en mods o futuras versiones del wiki."""
        wikitext = f"{{{{{alias}|blue|2 Chips}}}}"
        assert render_wikitext(wikitext) == "2 Chips"

    def test_c_with_nested_template(self):
        """Cuando el texto dentro de `{{c|...}}` contiene otra plantilla,
        debe aplanarse recursivamente.

        Caso real: `{{c|red|{{xmult|2}}}}` debe devolver 'x2 Mult', no
        'red' ni '{{xmult|2}}' literal."""
        assert render_wikitext("{{c|red|{{xmult|2}}}}") == "x2 Mult"

    def test_c_without_text_returns_empty(self):
        """Plantilla incompleta `{{c|red}}` — sin arg(2). El handler
        devuelve cadena vacía en lugar de petar."""
        # `arg(2)` con la nueva implementación recursiva: si no existe
        # arg(2), `node.has(2)` es False y devuelve "".
        assert render_wikitext("{{c|red}}") == ""


# =============================================================================
# Bug B: render recursivo de args en plantillas "identity"
# =============================================================================


class TestNestedTemplatesInsideIdentity:
    """Plantillas identity (j, tarot, v, etc.) con plantillas anidadas
    en sus args. Antes salía wikitext literal; ahora se aplana."""

    def test_joker_with_nested_hl(self):
        """`{{j|{{hl|red|JokerName}}}}` debe devolver 'JokerName'.

        Antes el handler de `j` hacía `return arg(1)` donde `arg(1)`
        stringificaba el Wikicode crudo, devolviendo literalmente
        '{{hl|red|JokerName}}'. Ahora `arg()` es recursivo."""
        assert render_wikitext("{{j|{{hl|red|JokerName}}}}") == "JokerName"

    def test_tarot_with_nested_c(self):
        """`{{tarot|{{c|purple|The Empress}}}}` debe devolver 'The Empress'.
        El bug afecta a TODA la familia identity, no solo a `j`."""
        assert render_wikitext("{{tarot|{{c|purple|The Empress}}}}") == "The Empress"

    def test_v_with_deep_nesting(self):
        """Nesting de 2+ niveles también debe funcionar. Verifica que
        render_node se recurseando es el camino correcto y no hay un
        cap de profundidad."""
        wikitext = "{{v|{{hl|orange|{{c|red|Tarot Merchant}}}}|...}}"
        assert render_wikitext(wikitext) == "Tarot Merchant"

    def test_mult_template_with_nested_color(self):
        """`{{mult|{{c|red|+4}}}}` debe devolver '+4 Mult'.
        El arg(1) recursivo permite que la cifra venga envuelta en una
        plantilla de color sin romper el formato."""
        assert render_wikitext("{{mult|{{c|red|+4}}}}") == "+4 Mult"


# =============================================================================
# Regresiones: lo que ya funcionaba debe seguir funcionando
# =============================================================================


class TestExistingBehaviorRegression:
    """Cualquier plantilla ya soportada antes del fix debe devolver
    EXACTAMENTE lo mismo. El fix no debería cambiar el output de
    casos simples."""

    @pytest.mark.parametrize(
        "wikitext,expected",
        [
            ("{{mult|+4}}", "+4 Mult"),
            ("{{chips|+30}}", "+30 Chips"),
            ("{{xmult|2}}", "x2 Mult"),
            ("{{xmult|+2}}", "x2 Mult"),  # lstrip('+')
            ("{{money|3}}", "$3"),
            ("{{stake|Gold}}", "Gold Stake"),
            ("{{suit|Diamond}}", "Diamond"),
            ("{{ph|Flush}}", "Flush"),
            ("{{j|Credit Card}}", "Credit Card"),
            ("{{tarot|The Empress}}", "The Empress"),
            ("{{d|Plasma}}", "Plasma"),
            ("{{spectral|Familiar}}", "Familiar"),
            ("{{blind|The Hook}}", "The Hook"),
            ("{{enhancement|Bonus}}", "Bonus"),
            ("{{edition|Foil}}", "Foil"),
            ("{{tag|Charm Tag}}", "Charm Tag"),
            ("{{sticker|Eternal}}", "Eternal"),
            ("{{sticker|Eternal|name=Vampire}}", "Vampire"),
            ("{{seal|Blue}}", "Blue"),
            ("{{seal|Blue|name=Blue Seals}}", "Blue Seals"),
            ("{{room}}", ""),
            ("", ""),
            (None, ""),
        ],
    )
    def test_known_template_outputs_unchanged(self, wikitext, expected):
        assert render_wikitext(wikitext) == expected

    def test_collapse_multiple_spaces(self):
        """`<br>` y comentarios HTML colapsan a un solo espacio."""
        wikitext = "Hola<br>mundo<!-- comentario -->!"
        assert render_wikitext(wikitext) == "Hola mundo !"


# =============================================================================
# Logging de templates desconocidos
# =============================================================================


class TestUnknownTemplateLogging:
    """El warning del unknown branch debe disparar para que las
    plantillas nuevas se detecten antes de aparecer rotas en BD."""

    def test_unknown_template_logs_warning(self, caplog):
        """Una plantilla no registrada genera WARNING con su nombre.

        Útil para el día que el wiki añada {{stickerStake|...}} u otra
        novedad: en lugar de bucear en descripciones rotas, se ve en
        los logs del seeder."""
        import logging

        with caplog.at_level(logging.WARNING, logger="app.scrapers.wiki"):
            result = render_wikitext("{{totallynewtemplate|hello|world}}")
        # Sigue funcionando con la heurística — devuelve arg(1).
        assert result == "hello"
        # Y avisa.
        assert any(
            "totallynewtemplate" in record.message for record in caplog.records
        )
