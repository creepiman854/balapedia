"""Tests unitarios de los parsers de la wiki de Balatro.

Organización: una clase por unidad lógica del módulo wiki.py. Cada test
valida un caso concreto contra una fixture real extraída de balatrowiki.org,
para garantizar que cualquier cambio en los parsers no rompe la extracción.
"""

from app.scrapers.wiki import (
    extract_leading_int,
    page_url,
    parse_consumable,
    parse_deck,
    parse_joker,
    parse_voucher,
    render_wikitext,
)

# ──────────────────────────────────────────────────────────────────────
#  Helpers genéricos
# ──────────────────────────────────────────────────────────────────────


class TestExtractLeadingInt:
    """Extracción de enteros desde campos que pueden contener texto adicional."""

    def test_clean_integer(self):
        assert extract_leading_int("42") == 42

    def test_integer_with_trailing_text(self):
        assert extract_leading_int("20 (cannot be found in shop)") == 20

    def test_negative_integer(self):
        assert extract_leading_int("-5 hand size") == -5

    def test_none_returns_none(self):
        assert extract_leading_int(None) is None

    def test_empty_string_returns_none(self):
        assert extract_leading_int("") is None

    def test_no_digits_returns_none(self):
        assert extract_leading_int("Available from start") is None


class TestRenderWikitext:
    """Aplanado de wikitexto con plantillas, wikilinks y HTML."""

    def test_plain_text_unchanged(self):
        assert render_wikitext("Hello world") == "Hello world"

    def test_mult_template(self):
        assert render_wikitext("{{Mult|+4}}") == "+4 Mult"

    def test_chips_template(self):
        assert render_wikitext("{{chips|+10}}") == "+10 Chips"

    def test_xmult_template_strips_plus(self):
        assert render_wikitext("{{xmult|+2}}") == "x2 Mult"

    def test_highlight_keeps_text_drops_color(self):
        assert render_wikitext("{{hl|orange|25%}}") == "25%"

    def test_money_template(self):
        assert render_wikitext("{{Money|2}}") == "$2"

    def test_stake_template(self):
        assert render_wikitext("{{Stake|Red}}") == "Red Stake"

    def test_wikilink_with_alias(self):
        assert render_wikitext("[[Cards|alias]]") == "alias"

    def test_wikilink_without_alias(self):
        assert render_wikitext("[[Joker]]") == "Joker"

    def test_br_tag_becomes_space(self):
        text = render_wikitext("Line one<br>Line two")
        assert "Line one Line two" in text

    def test_html_comment_dropped(self):
        text = render_wikitext("Visible<!-- hidden --> text")
        assert "hidden" not in text
        assert "Visible" in text and "text" in text

    def test_complex_real_world(self):
        raw = "Played cards with {{Suit|Diamond}} suit give {{Mult|+3}} when scored"
        result = render_wikitext(raw)
        assert "Diamond" in result
        assert "+3 Mult" in result

    def test_none_returns_empty_string(self):
        assert render_wikitext(None) == ""

    def test_wikilink_with_template_inside_alias(self):
        """Regresión: alias con plantilla anidada debe aplanarse, no salir crudo.

        Bug detectado durante la implementación del parser de Booster Packs:
        antes del fix, esto devolvía '{{hl|purple|Tarot}}' literal.
        """
        result = render_wikitext("[[Tarot Cards|{{hl|purple|Tarot}}]]")
        assert result == "Tarot"

    def test_small_tag_with_template_inside_contents(self):
        """Regresión: contents de <small> con plantilla anidada deben aplanarse."""
        result = render_wikitext("<small>{{hl|purple|The Fool}} excluded</small>")
        assert "The Fool excluded" in result
        assert "{{" not in result


class TestPageUrl:
    """Construcción de URLs públicas de la wiki."""

    def test_simple_title(self):
        assert page_url("Joker") == "https://balatrowiki.org/wiki/Joker"

    def test_title_with_spaces_uses_underscores(self):
        assert page_url("Mr. Bones") == "https://balatrowiki.org/wiki/Mr._Bones"


# ──────────────────────────────────────────────────────────────────────
#  parse_joker
# ──────────────────────────────────────────────────────────────────────


class TestParseJoker:
    """Parser de la plantilla Joker info."""

    def test_base_joker(self, load_wiki_fixture):
        result = parse_joker(load_wiki_fixture("joker"))
        assert result["type"] == "joker"
        assert result["item_number"] == 1
        assert result["name"] == "Joker"
        assert result["rarity"] == "Common"
        assert result["effect_type"] == "Additive Mult"
        assert result["activation"] == "Independent"
        assert result["buy_price"] == 2
        assert result["sell_price"] == 1  # auto-calculado: 2 // 2
        assert result["in_shop"] is True
        assert result["is_copyable"] is True
        assert result["is_perishable"] is True
        assert result["is_eternal"] is True
        assert result["has_negative_variant"] is True
        assert result["description"] == "+4 Mult"
        assert result["unlock_condition"] == "Available from start."

    def test_greedy_joker_with_score_template_in_effect(self, load_wiki_fixture):
        result = parse_joker(load_wiki_fixture("greedy_joker"))
        assert result["item_number"] == 2
        assert result["name"] == "Greedy Joker"
        assert "Diamond" in result["description"]
        assert "+3 Mult" in result["description"]
        assert result["activation"] == "On Scored"

    def test_mr_bones_with_unlock_and_complex_effect(self, load_wiki_fixture):
        result = parse_joker(load_wiki_fixture("mr_bones"))
        assert result["name"] == "Mr. Bones"
        assert result["rarity"] == "Uncommon"
        assert result["is_copyable"] is False
        assert result["is_eternal"] is False
        assert result["is_perishable"] is True
        assert result["unlock_condition"] == "Lose 5 runs"
        # El efecto incluye <br> entre dos highlights: deben fundirse en un texto
        assert "25%" in result["description"]
        assert "self destructs" in result["description"]

    def test_triboulet_legendary_dirty_buyprice(self, load_wiki_fixture):
        result = parse_joker(load_wiki_fixture("triboulet"))
        assert result["rarity"] == "Legendary"
        # buyprice = "20 (cannot be found in shop)" -> entero limpio + flag
        assert result["buy_price"] == 20
        assert result["in_shop"] is False
        # sellprice override (no es buyprice / 2)
        assert result["sell_price"] == 10
        # xmult template
        assert "x2 Mult" in result["description"]
        # unlock con wikilinks anidados y plantilla hl: debe leerse limpio
        assert "Soul" in result["unlock_condition"]
        assert "Joker" in result["unlock_condition"]

    def test_returns_none_for_non_joker_template(self, load_wiki_fixture):
        # Pasarle un Voucher al parser de Joker debe devolver None, no romper
        assert parse_joker(load_wiki_fixture("overstock")) is None

    def test_returns_none_for_empty_input(self):
        assert parse_joker("") is None


# ──────────────────────────────────────────────────────────────────────
#  parse_consumable
# ──────────────────────────────────────────────────────────────────────


class TestParseConsumable:
    """Parser unificado de Tarots, Planets y Spectrals."""

    def test_tarot_the_fool(self, load_wiki_fixture):
        result = parse_consumable(load_wiki_fixture("the_fool"))
        assert result["type"] == "tarot"
        assert result["name"] == "The Fool"
        assert result["item_number"] == 1
        assert result["buy_price"] == 3
        assert result["sell_price"] == 1
        assert result["in_shop"] is True

    def test_tarot_the_hierophant(self, load_wiki_fixture):
        result = parse_consumable(load_wiki_fixture("the_hierophant"))
        assert result["type"] == "tarot"
        assert result["item_number"] == 7
        assert "Bonus Cards" in result["description"]

    def test_planet_pluto(self, load_wiki_fixture):
        result = parse_consumable(load_wiki_fixture("pluto"))
        assert result["type"] == "planet"
        assert result["name"] == "Pluto"
        # Plantillas {{ph|...}}, {{mult|...}}, {{chips|...}} deben aplanarse
        assert "High Card" in result["description"]
        assert "+1 Mult" in result["description"]
        assert "+10 Chips" in result["description"]

    def test_planet_jupiter(self, load_wiki_fixture):
        result = parse_consumable(load_wiki_fixture("jupiter"))
        assert result["type"] == "planet"
        assert result["item_number"] == 6
        assert "Flush" in result["description"]

    def test_spectral_ectoplasm_with_html_comment(self, load_wiki_fixture):
        result = parse_consumable(load_wiki_fixture("ectoplasm"))
        assert result["type"] == "spectral"
        assert result["sell_price"] == 2  # 4 // 2
        # El comentario HTML no debe aparecer en la descripción
        assert "yes, the" not in result["description"]
        assert "Negative" in result["description"]

    def test_spectral_the_soul_dirty_buyprice(self, load_wiki_fixture):
        result = parse_consumable(load_wiki_fixture("the_soul"))
        assert result["type"] == "spectral"
        assert result["buy_price"] == 4
        assert result["in_shop"] is False  # "(cannot be found in shop)"
        assert result["sell_price"] == 2  # override explícito


# ──────────────────────────────────────────────────────────────────────
#  parse_deck
# ──────────────────────────────────────────────────────────────────────


class TestParseDeck:
    """Parser de la plantilla Deck info."""

    def test_red_deck(self, load_wiki_fixture):
        result = parse_deck(load_wiki_fixture("red_deck"))
        assert result["type"] == "deck"
        assert result["item_number"] == 1
        assert result["name"] == "Red Deck"
        # El campo se llama "limit", no "effect" -> debe leerse igual
        assert "+1 discard" in result["description"]
        assert result["unlock_condition"] == "Unlocked from start"

    def test_zodiac_deck_with_complex_unlock(self, load_wiki_fixture):
        result = parse_deck(load_wiki_fixture("zodiac_deck"))
        assert result["item_number"] == 11
        # El unlock referencia un Stake con plantilla
        assert "Red Stake" in result["unlock_condition"]
        # La descripción referencia varios vouchers vía {{V|...}}
        assert "Tarot Merchant" in result["description"]
        assert "Planet Merchant" in result["description"]
        assert "Overstock" in result["description"]


# ──────────────────────────────────────────────────────────────────────
#  parse_voucher
# ──────────────────────────────────────────────────────────────────────


class TestParseVoucher:
    """Parser de la plantilla Voucher info, incluyendo cadena Base/Upgraded."""

    def test_overstock_base_chains_to_upgrade(self, load_wiki_fixture):
        result = parse_voucher(load_wiki_fixture("overstock"))
        assert result["type"] == "voucher"
        assert result["voucher_tier"] == "Base"
        assert result["next_voucher_name"] == "Overstock Plus"
        assert result["item_number"] is None  # asignado durante seed
        assert "card slot" in result["description"]

    def test_blank_chains_to_antimatter(self, load_wiki_fixture):
        result = parse_voucher(load_wiki_fixture("blank"))
        assert result["next_voucher_name"] == "Antimatter"
        assert "Does nothing" in result["description"]

    def test_seed_money_base_with_money_template(self, load_wiki_fixture):
        result = parse_voucher(load_wiki_fixture("seed_money"))
        assert result["voucher_tier"] == "Base"
        assert result["next_voucher_name"] == "Money Tree"
        # La plantilla {{Money|10}} debe expandirse a "$10"
        assert "$10" in result["description"]

    def test_money_tree_upgraded_with_unlock(self, load_wiki_fixture):
        result = parse_voucher(load_wiki_fixture("money_tree"))
        assert result["voucher_tier"] == "Upgraded"
        # Upgraded vales no enlazan a otro vale
        assert result["next_voucher_name"] is None
        # Tiene unlock real, no el default
        assert "ten consecutive rounds" in result["unlock_condition"]
        assert "$20" in result["description"]


# ──────────────────────────────────────────────────────────────────────
#  parse_booster_packs_page  (parser de wikitable, no de infobox)
# ──────────────────────────────────────────────────────────────────────


class TestParseBoosterPacksPage:
    """Parser de la wikitable de la página 'Booster Packs'.

    A diferencia del resto, este parser opera sobre la página completa y
    devuelve una lista de packs (no un único dict). La fixture es la
    página real de la wiki tal como la devuelve la API en el momento de
    capturarla.
    """

    def test_returns_15_packs(self, load_wiki_fixture):
        """5 categorías × 3 tamaños = 15 booster packs en el juego base."""
        from app.scrapers.wiki import parse_booster_packs_page

        packs = parse_booster_packs_page(load_wiki_fixture("booster_packs"))
        assert len(packs) == 15

    def test_full_distribution_by_type_and_size(self, load_wiki_fixture):
        """Cada combinación (pack_type, size) aparece exactamente una vez."""
        from collections import Counter
        from app.scrapers.wiki import parse_booster_packs_page

        packs = parse_booster_packs_page(load_wiki_fixture("booster_packs"))
        ctr = Counter((p["pack_type"], p["size"]) for p in packs)
        assert len(ctr) == 15
        assert all(n == 1 for n in ctr.values())

    def test_arcana_pack_basic_fields(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_booster_packs_page

        packs = parse_booster_packs_page(load_wiki_fixture("booster_packs"))
        arcana = next(p for p in packs if p["name"] == "Arcana Pack")
        assert arcana["pack_type"] == "Arcana"
        assert arcana["size"] == "Normal"
        assert arcana["cost"] == 4
        assert arcana["image_filename"] == "Arcana Normal 1.png"
        # Descripción ya aplanada (sin wikitext crudo)
        assert "Tarot" in arcana["description"]
        assert "{{" not in arcana["description"]

    def test_costs_follow_size_pattern(self, load_wiki_fixture):
        """Convención del juego: Normal=$4, Jumbo=$6, Mega=$8 en todos los tipos."""
        from app.scrapers.wiki import parse_booster_packs_page

        packs = parse_booster_packs_page(load_wiki_fixture("booster_packs"))
        for p in packs:
            if p["size"] == "Normal":
                assert p["cost"] == 4, f"{p['name']} (Normal) debería costar 4"
            elif p["size"] == "Jumbo":
                assert p["cost"] == 6, f"{p['name']} (Jumbo) debería costar 6"
            elif p["size"] == "Mega":
                assert p["cost"] == 8, f"{p['name']} (Mega) debería costar 8"

    def test_descriptions_are_fully_flattened(self, load_wiki_fixture):
        """Ningún pack debe tener wikitext crudo en su descripción."""
        from app.scrapers.wiki import parse_booster_packs_page

        packs = parse_booster_packs_page(load_wiki_fixture("booster_packs"))
        for p in packs:
            desc = p["description"]
            assert "{{" not in desc, f"Template crudo en {p['name']}: {desc}"
            assert "}}" not in desc
            assert "[[" not in desc
            assert "]]" not in desc

    def test_buffoon_packs_describe_jokers(self, load_wiki_fixture):
        """Buffoon Packs ofrecen Jokers; sus descripciones lo deben mencionar."""
        from app.scrapers.wiki import parse_booster_packs_page

        packs = parse_booster_packs_page(load_wiki_fixture("booster_packs"))
        buffoon = [p for p in packs if p["pack_type"] == "Buffoon"]
        assert len(buffoon) == 3
        for p in buffoon:
            assert "Joker" in p["description"]

    def test_each_pack_has_required_fields(self, load_wiki_fixture):
        """Esquema mínimo de cada dict devuelto."""
        from app.scrapers.wiki import parse_booster_packs_page

        required = {
            "type",
            "name",
            "pack_type",
            "size",
            "cost",
            "description",
            "image_filename",
        }
        packs = parse_booster_packs_page(load_wiki_fixture("booster_packs"))
        for p in packs:
            assert set(p.keys()) >= required, f"Falta algún campo en {p}"

    def test_returns_empty_list_if_no_table_section(self):
        """Si la página no tiene la sección esperada, devuelve []."""
        from app.scrapers.wiki import parse_booster_packs_page

        assert parse_booster_packs_page("Just some random wikitext") == []
