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

    def test_tag_template(self):
        assert render_wikitext("{{Tag|Uncommon}}") == "Uncommon"

    def test_blind_template(self):
        assert render_wikitext("{{Blind|Crimson Heart}}") == "Crimson Heart"

    def test_enhancement_template(self):
        assert render_wikitext("{{Enhancement|Bonus}}") == "Bonus"

    def test_edition_template(self):
        assert render_wikitext("{{Edition|Polychrome}}") == "Polychrome"

    def test_spectral_template(self):
        assert render_wikitext("{{Spectral|Wraith}}") == "Wraith"

    def test_sticker_with_name_uses_name(self):
        """Sticker con `name=` usa el name (más legible que el tipo)."""
        result = render_wikitext(
            "{{Sticker|Eternal|image=Vampire.png|link=Vampire|name=Vampire}}"
        )
        assert result == "Vampire"

    def test_sticker_without_name_falls_back_to_type(self):
        """Sticker sin `name=` cae al primer arg (tipo de sticker)."""
        assert render_wikitext("{{Sticker|Eternal}}") == "Eternal"

    def test_seal_with_name_uses_name(self):
        result = render_wikitext("{{Seal|Blue|name=Blue Seals}}")
        assert result == "Blue Seals"

    def test_seal_without_name_falls_back_to_color(self):
        assert render_wikitext("{{Seal|Blue}}") == "Blue"


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


# ──────────────────────────────────────────────────────────────────────
#  parse_challenge_deck
# ──────────────────────────────────────────────────────────────────────


class TestParseChallengeDeck:
    """Parser de la plantilla 'Challenge info' de los Challenge Decks.

    Los 6 fixtures cubren toda la combinatoria relevante:
      - X-ray Vision: el más simple, solo `modifier`.
      - Jokerless: banned complejo multilínea, sin starter.
      - Non-Perishable: banned inline simple, sin starter.
      - Bram Poker: starter rico (sticker + tarots + vouchers), sin banned.
      - Five-Card Draw: starter + banned.
      - Mad World: starter + banned + deck modificado (caso completo).
    """

    def test_x_ray_vision_minimal(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_challenge_deck

        result = parse_challenge_deck(load_wiki_fixture("challenge_x_ray_vision"))
        assert result["type"] == "challenge_deck"
        assert result["item_number"] == 5
        assert result["name"] == "X-ray Vision"
        assert "1 in 4" in result["modifier"]
        # Sin starter, banned ni deck en este challenge
        assert result["starter"] is None
        assert result["banned"] is None
        assert result["deck_description"] is None

    def test_jokerless_complex_banned(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_challenge_deck

        result = parse_challenge_deck(load_wiki_fixture("challenge_jokerless"))
        assert result["item_number"] == 20
        assert result["name"] == "Jokerless"
        # El modifier menciona "shop" y "0 Joker Slots" tras renderizar
        assert "shop" in result["modifier"].lower()
        assert "0" in result["modifier"]
        assert result["starter"] is None
        # banned debe contener referencias a múltiples categorías
        assert result["banned"] is not None
        for keyword in ("Tarot", "Spectral", "Tags", "Blinds", "Vouchers"):
            assert keyword in result["banned"]
        # Items concretos
        for item in ("Judgement", "Wraith", "Antimatter"):
            assert item in result["banned"]

    def test_non_perishable_inline_banned(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_challenge_deck

        result = parse_challenge_deck(load_wiki_fixture("challenge_non_perishable"))
        assert result["name"] == "Non-Perishable"
        assert result["item_number"] == 8
        assert "Eternal" in result["modifier"]
        # Banned inline con varios jokers
        assert result["banned"] is not None
        for joker in ("Gros Michel", "Cavendish", "Ice Cream", "Ramen"):
            assert joker in result["banned"]

    def test_bram_poker_starter_with_sticker_and_consumables(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_challenge_deck

        result = parse_challenge_deck(load_wiki_fixture("challenge_bram_poker"))
        assert result["name"] == "Bram Poker"
        assert result["item_number"] == 13
        # Starter debe mencionar Vampire, las dos Tarots y los dos Vouchers
        assert result["starter"] is not None
        for item in (
            "Vampire",
            "The Emperor",
            "The Empress",
            "Magic Trick",
            "Illusion",
        ):
            assert item in result["starter"]
        # Sin banned ni deck modificado
        assert result["banned"] is None
        assert result["deck_description"] is None

    def test_five_card_draw_starter_and_banned(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_challenge_deck

        result = parse_challenge_deck(load_wiki_fixture("challenge_five_card_draw"))
        assert result["name"] == "Five-Card Draw"
        assert result["item_number"] == 17
        # Starter: Card Sharp y Joker
        assert "Card Sharp" in result["starter"]
        assert "Joker" in result["starter"]
        # Banned: 3 jokers concretos
        for joker in ("Juggler", "Troubadour", "Turtle Bean"):
            assert joker in result["banned"]
        assert result["deck_description"] is None

    def test_mad_world_complete_case(self, load_wiki_fixture):
        """Mad World tiene los 4 campos opcionales rellenos."""
        from app.scrapers.wiki import parse_challenge_deck

        result = parse_challenge_deck(load_wiki_fixture("challenge_mad_world"))
        assert result["name"] == "Mad World"
        assert result["item_number"] == 6
        # Modifier menciona "Hands" e "Interest"
        assert "Hands" in result["modifier"]
        assert "Interest" in result["modifier"]
        # Starter: Pareidolia y Business Card
        assert "Pareidolia" in result["starter"]
        assert "Business Card" in result["starter"]
        # Banned: The Plant
        assert "The Plant" in result["banned"]
        # Deck modificado: 32 cartas, ranks 2-9
        assert result["deck_description"] is not None
        assert "32" in result["deck_description"]

    def test_image_filename_always_none(self, load_wiki_fixture):
        """La plantilla Challenge info no expone imagen."""
        from app.scrapers.wiki import parse_challenge_deck

        for slug in ("jokerless", "bram_poker", "x_ray_vision"):
            result = parse_challenge_deck(load_wiki_fixture(f"challenge_{slug}"))
            assert result["image_filename"] is None

    def test_descriptions_are_fully_flattened(self, load_wiki_fixture):
        """Ningún campo descriptivo debe tener wikitext crudo tras renderizar."""
        from app.scrapers.wiki import parse_challenge_deck

        for slug in (
            "jokerless",
            "bram_poker",
            "mad_world",
            "five_card_draw",
            "non_perishable",
            "x_ray_vision",
        ):
            result = parse_challenge_deck(load_wiki_fixture(f"challenge_{slug}"))
            for field in ("modifier", "starter", "banned", "deck_description"):
                value = result.get(field)
                if value is None:
                    continue
                assert (
                    "{{" not in value
                ), f"Wikitext crudo en {result['name']!r}.{field}: {value}"
                assert "}}" not in value
                assert "[[" not in value
                assert "]]" not in value

    def test_returns_none_for_non_challenge_template(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_challenge_deck

        # Pasarle un Joker debe devolver None
        assert parse_challenge_deck(load_wiki_fixture("joker")) is None


# ──────────────────────────────────────────────────────────────────────
#  parse_stakes_page
# ──────────────────────────────────────────────────────────────────────


class TestParseStakesPage:
    """Parser de la wikitable de Stakes (datos de referencia)."""

    def test_returns_8_stakes(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_stakes_page

        stakes = parse_stakes_page(load_wiki_fixture("stakes_page"))
        assert len(stakes) == 8

    def test_stake_order_is_sequential(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_stakes_page

        stakes = parse_stakes_page(load_wiki_fixture("stakes_page"))
        orders = sorted(s["stake_order"] for s in stakes)
        assert orders == list(range(1, 9))

    def test_white_stake_basic(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_stakes_page

        stakes = parse_stakes_page(load_wiki_fixture("stakes_page"))
        white = next(s for s in stakes if s["name"] == "White Stake")
        assert white["stake_order"] == 1
        assert white["color"] == "White"
        assert white["unlocks_deck_name"] is None  # White no desbloquea deck
        assert "base difficulty" in white["effect_description"].lower()

    def test_red_stake_unlocks_zodiac_deck(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_stakes_page

        stakes = parse_stakes_page(load_wiki_fixture("stakes_page"))
        red = next(s for s in stakes if s["name"] == "Red Stake")
        assert red["stake_order"] == 2
        assert red["color"] == "Red"
        assert red["unlocks_deck_name"] == "Zodiac"

    def test_all_stakes_have_image_filename(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_stakes_page

        stakes = parse_stakes_page(load_wiki_fixture("stakes_page"))
        for s in stakes:
            assert s["image_filename"], f"Falta imagen en {s['name']}"

    def test_returns_empty_list_for_unrelated_wikitext(self):
        from app.scrapers.wiki import parse_stakes_page

        assert parse_stakes_page("Random text without table") == []


# ──────────────────────────────────────────────────────────────────────
#  parse_blind
# ──────────────────────────────────────────────────────────────────────


class TestParseBlind:
    """Parser de la plantilla Blind info."""

    def test_the_hook_basic_fields(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_blind

        result = parse_blind(load_wiki_fixture("blind_the_hook"))
        assert result["name"] == "The Hook"
        assert result["blind_type"] == "Boss"
        assert result["ante"] == "Any"
        assert result["score_multiplier"] == 2.0
        assert result["reward_money"] == 5
        assert result["matador_compatible"] is False  # compat-matador = no
        assert "Discards 2" in result["description"]

    def test_the_plant_boss_with_minimum_ante(self, load_wiki_fixture):
        """The Plant es un Boss regular con minimum ante=4 (no finisher)."""
        from app.scrapers.wiki import parse_blind

        result = parse_blind(load_wiki_fixture("blind_the_plant"))
        assert result["blind_type"] == "Boss"

    def test_returns_none_for_non_blind_template(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_blind

        # Joker no es Blind
        assert parse_blind(load_wiki_fixture("joker")) is None

    def test_all_required_fields_present(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_blind

        result = parse_blind(load_wiki_fixture("blind_the_hook"))
        required = {
            "name",
            "image_filename",
            "blind_type",
            "description",
            "ante",
            "score_multiplier",
            "reward_money",
            "matador_compatible",
        }
        assert set(result.keys()) >= required

    def test_amber_acorn_is_showdown_finisher(self, load_wiki_fixture):
        """Los 5 finisher blinds tienen type=Showdown (no Boss) en la wiki."""
        from app.scrapers.wiki import parse_blind

        result = parse_blind(load_wiki_fixture("blind_amber_acorn"))
        assert result["name"] == "Amber Acorn"
        assert result["blind_type"] == "Showdown"
        assert result["ante"] == "8"
        assert result["score_multiplier"] == 2.0
        assert result["reward_money"] == 8
        assert result["matador_compatible"] is False


# ──────────────────────────────────────────────────────────────────────
#  parse_tag
# ──────────────────────────────────────────────────────────────────────


class TestParseTag:
    """Parser de la plantilla Tag info."""

    def test_double_tag_no_unlock(self, load_wiki_fixture):
        """Double Tag no tiene unlock condition."""
        from app.scrapers.wiki import parse_tag

        result = parse_tag(load_wiki_fixture("tag_double"))
        assert result["name"] == "Double Tag"
        assert result["ante"] == "Any"
        assert result["unlock_condition"] is None
        assert "copy" in result["description"].lower()

    def test_negative_tag_with_unlock(self, load_wiki_fixture):
        """Negative Tag requiere descubrir la edición Negative."""
        from app.scrapers.wiki import parse_tag

        result = parse_tag(load_wiki_fixture("tag_negative"))
        assert result["name"] == "Negative Tag"
        assert result["ante"] == "2+"
        assert result["unlock_condition"] is not None
        assert "Negative" in result["unlock_condition"]
        assert "Discover" in result["unlock_condition"]

    def test_polychrome_tag_basic(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_tag

        result = parse_tag(load_wiki_fixture("tag_polychrome"))
        assert result["name"] == "Polychrome Tag"
        assert result["unlock_condition"] is not None
        assert "Polychrome" in result["unlock_condition"]

    def test_descriptions_fully_flattened(self, load_wiki_fixture):
        """Ningún Tag debe tener wikitext o HTML crudo en su descripción."""
        from app.scrapers.wiki import parse_tag

        for slug in ("tag_double", "tag_negative", "tag_polychrome"):
            result = parse_tag(load_wiki_fixture(slug))
            d = result["description"]
            assert "{{" not in d, f"Template crudo en {result['name']}: {d}"
            assert "[[" not in d
            assert "<small>" not in d  # regresión del fix de hl

    def test_returns_none_for_non_tag_template(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_tag

        assert parse_tag(load_wiki_fixture("joker")) is None


# ──────────────────────────────────────────────────────────────────────
#  parse_card_modifier
# ──────────────────────────────────────────────────────────────────────


class TestParseCardModifier:
    """Parser de plantilla Modifier info (3 tipos en una sola plantilla)."""

    def test_foil_is_edition(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        result = parse_card_modifier(load_wiki_fixture("modifier_foil"))
        assert result["name"] == "Foil"
        assert result["modifier_type"] == "Edition"
        assert "Chips" in result["effect"] or "50" in result["effect"]
        assert result["image_filename"]

    def test_polychrome_is_edition_with_xmult(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        result = parse_card_modifier(load_wiki_fixture("modifier_polychrome"))
        assert result["modifier_type"] == "Edition"
        # Polychrome típicamente da xMult
        assert result["effect"]

    def test_gold_seal_is_seal(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        result = parse_card_modifier(load_wiki_fixture("modifier_gold_seal"))
        assert result["name"] == "Gold Seal"
        assert result["modifier_type"] == "Seal"
        assert "$3" in result["effect"] or "money" in result["effect"].lower()

    def test_red_seal_is_seal(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        result = parse_card_modifier(load_wiki_fixture("modifier_red_seal"))
        assert result["modifier_type"] == "Seal"

    def test_bonus_is_enhancement(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        result = parse_card_modifier(load_wiki_fixture("modifier_bonus_cards"))
        assert result["modifier_type"] == "Enhancement"

    def test_steel_is_enhancement(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        result = parse_card_modifier(load_wiki_fixture("modifier_steel_cards"))
        assert result["modifier_type"] == "Enhancement"

    def test_descriptions_are_flattened(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        for slug in (
            "modifier_foil",
            "modifier_gold_seal",
            "modifier_bonus_cards",
            "modifier_steel_cards",
        ):
            result = parse_card_modifier(load_wiki_fixture(slug))
            assert result is not None
            e = result["effect"]
            assert "{{" not in e, f"Template crudo en {result['name']}: {e}"
            assert "[[" not in e

    def test_returns_none_for_non_modifier_template(self, load_wiki_fixture):
        from app.scrapers.wiki import parse_card_modifier

        assert parse_card_modifier(load_wiki_fixture("joker")) is None
