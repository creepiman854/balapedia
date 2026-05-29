"""Cliente de la MediaWiki API y parsers de plantillas de la wiki de Balatro."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional
from urllib.parse import quote

import mwparserfromhell
import requests
from mwparserfromhell.nodes import Comment, HTMLEntity, Tag, Template, Wikilink

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Configuraciones
# ──────────────────────────────────────────────────────────────────────
WIKI_API_URL = "https://balatrowiki.org/api.php"
WIKI_BASE_URL = "https://balatrowiki.org"

_default_ua = "BalapediaTFG/0.1"
_ua_from_env = (os.getenv("WIKI_USER_AGENT") or "").strip()
USER_AGENT = _ua_from_env if _ua_from_env else _default_ua

REQUEST_TIMEOUT_S = 15
HEADERS = {"User-Agent": USER_AGENT}

# Constantes para render_wikitext
COLOR_DISCARD_TEMPLATES = {"hl", "c", "color", "fc", "clr", "textcolor"}
IDENTITY_TEMPLATES = {
    "suit",
    "v",
    "j",
    "tarot",
    "d",
    "spectral",
    "blind",
    "enhancement",
    "edition",
    "tag",
}

# Overrides manuales
DESCRIPTION_OVERRIDES: dict[str, str] = {
    # Jokers
    "Erosion": "+4 Mult for each card below the deck's starting size in your full deck",
    "Mail-In Rebate": "Earn $5 for each discarded rank, rank changes every round",
    "Ancient Joker": "Each played card with suit gives x1.5 Mult when scored, suit changes at end of round",
    "Castle": "This Joker gains +3 Chips per discarded suit card, suit changes every round",
    "The Idol": "Each played rank of suit gives x2 Mult when scored <small>Card changes every round</small>",
    "To Do List": "Win $4 depending on the poker hand selected <small>Poker hands change at the end of the round</small>",
    "Ride the Bus": "This Joker gains +1 Mult per consecutive hand played without a scoring face card",
    "Runner": "Gains +15 Chips if played hand contains a Straight",
    "Blue Joker": "+2 Chips for each remaining card in deck",
    "Green Joker": "+1 Mult per hand played -1 Mult per discard",
    "Fortune Teller": "+1 Mult per Tarot card used this run",
    "Swashbuckler": "Adds the sell value of all other owned Jokers to Mult",
    "Ceremonial Dagger": "When Blind is selected, destroy Joker to the right and permanently add double its sell value to this Mult",
    "Abstract Joker": "+3 Mult for each Joker card",
    "Red Card": "This Joker gains +3 Mult when any Booster Pack is skipped",
    "Stone Joker": "Gives +25 Chips for each Stone Card in your full deck",
    "Bull": "+2 Chips for each $1 you have",
    "Flash Card": "This Joker gains +2 Mult per reroll in the shop",
    "Spare Trousers": "+2 Mult if played hand contains a Two Pair",
    "Wee Joker": "This Joker gains +8 Chips when each played 2 is scored",
    "Bootstraps": "+2 Mult for every $5 you have",
    "Loyalty Card": "x4 Mult every 6 hands played <small>Starts at 5, -1 each time it is triggered</small>",
    "Hack": "Retrigger each played 2, 3, 4, or 5",
    "Ice Cream": "+100 Chips. -5 Chips for every hand played",
    "Baseball Card": "Uncommon Jokers each give x1.5 Mult",
    "Popcorn": "+20 Mult. -4 Mult per round played",
    "Showman": "Joker, Tarot, Planet, and Spectral cards may appear multiple times",
    "Baron": "Each King held in hand gives x1.5 Mult",
    # Booster Packs
    "Arcana Pack": "Choose 1 of up to 3 Tarot Cards",
    "Celestial Pack": "Choose 1 of up to 3 Planet Cards",
    "Standard Pack": "Choose 1 of up to 5 Playing Cards to add to your deck",
    "Buffoon Pack": "Choose 1 of up to 2 Joker cards",
    "Spectral Pack": "Choose 1 of up to 2 Spectral cards",
    # Decks
    "Anaglyph Deck": "After defeating each Boss Blind, gain a Double Tag",
    "Black Deck": "+1 Joker slot\n-1 hand every round",
    "Nebula Deck": "Start run with the Telescope voucher\n-1 consumable slot",
    "Plasma Deck": "Balance Chips and Mult when calculating score for played hand\nX2 base Blind size",
    # Card Modifiers
    "Glass Card": "x2 Mult. 1 in 4 chance to destroy card",
    "Stone Card": "+50. Chips no rank or suit",
    "Lucky Card": "1 in 5 chance for +20 Mult. 1 in 15 chance to win $20",
    # Tags
    "Double Tag": "Gives a copy of the next selected Tag <small>Double Tag excluded</small>",
    "Garbage Tag": "Gives $1 per unused discard this run",
    "Handy Tag": "Gives $1 per played hand this run",
    "Speed Tag": "Gives $5 per skipped Blind this run",
}

# Overrides manuales de Challenge Decks
CHALLENGE_MODIFIER_OVERRIDES: dict[str, str] = {
    "The Omelette": "All Blinds give no reward money\nExtra Hands no longer earn money\nEarn no Interest at end of round",
    "Rich get Richer": "Chips cannot exceed the current $\nStart with $100",
    "Mad World": "Extra Hands no longer earn money\nEarn no Interest at end of round",
    "Luxury Tax": "Hold -1 cards in hand for every $5 you have\n10 hand size",
    "Typecast": "When ante 4 boss is defeated:\n- all Jokers become eternal\n- set Joker slots to 0",
    "Blast Off": "2 hands per round\n2 discards per round\n4 Joker Slots",
    "Five-Card Draw": "6 discards per round\n5 hand size\n7 Joker slots",
    "Golden Needle": "Discards each cost $1\n\n1 hands per round\n6 discards per round\nStart with $10",
    "Cruelty": "Small Blinds give no reward money\nBig Blinds give no reward money\n\n3 Joker Slots",
    "Jokerless": "Jokers no longer appear in the shop\n\n0 Joker Slots",
}

CHALLENGE_STARTER_OVERRIDES: dict[str, str] = {
    "15 Minute City": "Eternal Ride the Bus\nEternal Shortcut",
    "Rich get Richer": "Seed Money\nMoney Tree",
    "On a Knife's Edge": "Eternal, Pinned Ceremonial Dagger\nThe Pinned Joker is always in the leftmost position",
    "Mad World": "Eternal, Negative Pareidolia\nEternal Business Card",
    "Medusa": "Eternal Marble Joker",
    "Inflation": "Credit Card",
    "Bram Poker": "Eternal Vampire\nThe Emperor,  The Empress\nMagic Trick,  Illusion",
    "Fragile": "2x Eternal, Negative Oops! All 6s",
    "Monolith": "Eternal Obelisk\nEternal Negative Marble Joker",
    "Blast Off": "Eternal Constellation\nEternal Rocket\nPlanet Merchant\nPlanet Tycoon",
    "Five-Card Draw": "Card Sharp\nJoker",
    "Golden Needle": "Credit Card",
}

CHALLENGE_BANNED_OVERRIDES: dict[str, str] = {
    "The Omelette": "Banned Vouchers:\nSeed Money\nMoney Tree\n\nBanned Jokers:\n To the Moon\n Rocket\n Golden Joker\n Satellite",
    "Mad World": "Banned Blinds:\nThe Plant",
    "Non-Perishable": "Banned Jokers:  \nGros Michel, Cavendish\nIce Cream, Turtle Bean\nRamen, Diet Cola\nSeltzer, Popcorn\nMr. Bones, Invisible Joker\nLuchador\n\nBanned Blinds:\nVerdant Leaf",
    "Typecast": "Banned Blinds:\nVerdant Leaf",
    "Inflation": "Banned Vouchers:\nClearance Sale\nLiquidation",
    "Fragile": "All methods of adding non-glass cards or removing glass enhancements are banned:\n\n- Jokers:  \nMarble Joker, Vampire\nMidas Mask, Certificate\n\n- Tarot cards:\nThe Magician, The Empress\nThe Hierophant, The Chariot\nThe Devil, The Tower\nThe Lovers\n\n- Spectral cards:\nIncantation, Grim\nFamiliar\n\n- Vouchers:\nMagic Trick, Illusion\n\n- Booster Packs: \nStandard Pack\n\n- Tags:\nStandard Tag",
    "Blast Off": "Banned Vouchers:  \nGrabber, Nacho Tong\n\nBanned Jokers:\nBurglar",
    "Five-Card Draw": "Banned Jokers:\nJuggler, Troubadour\nTurtle Bean",
    "Golden Needle": "Banned Jokers:\nBurglar\n\nBanned Vouchers:\nGrabber\nNacho Tong",
    "Jokerless": "All methods of acquiring Jokers:\n\n- Tarot cards:\nJudgement\n\n- Spectral cards:\nWraith, The Soul\n\n- Tags:\nUncommon Tag,  Rare Tag\nNegative Tag, Foil Tag\nHolographic Tag, Polychrome Tag\nBuffoon Tag, Top-up Tag\n\n- Blinds:\nCrimson Heart, Verdant Leaf\nAmber Acorn\n\n- Vouchers:\nAntimatter\n\n- Booster Packs:\nall 4 Buffoon Packs",
}

# ──────────────────────────────────────────────────────────────────────
# 1. Cliente HTTP
# ──────────────────────────────────────────────────────────────────────


def fetch_wikitext(title: str) -> Optional[str]:
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": title,
        "format": "json",
        "formatversion": 2,
    }
    response = requests.get(
        WIKI_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_S
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    revisions = pages[0].get("revisions", [])
    return revisions[0]["slots"]["main"]["content"] if revisions else None


def list_pages_in_category(category: str, limit: int = 500) -> list[str]:
    titles = []
    cmcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": limit,
            "cmtype": "page",
            "format": "json",
            "formatversion": 2,
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue
        response = requests.get(
            WIKI_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_S
        )
        response.raise_for_status()
        data = response.json()
        members = data.get("query", {}).get("categorymembers", [])
        titles.extend(m["title"] for m in members)
        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break
    return titles


def resolve_image_url(filename: str) -> Optional[str]:
    if not filename:
        return None
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "formatversion": 2,
    }
    response = requests.get(
        WIKI_API_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_S
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    imageinfo = pages[0].get("imageinfo", [])
    return imageinfo[0].get("url") if imageinfo else None


def page_url(title: str) -> str:
    return f"{WIKI_BASE_URL}/wiki/{quote(title.replace(' ', '_'))}"


# ──────────────────────────────────────────────────────────────────────
# 2. Utilidades de parseo
# ──────────────────────────────────────────────────────────────────────


def _get_template(wikitext: str, template_name: str) -> Optional[Template]:
    code = mwparserfromhell.parse(wikitext)
    templates = code.filter_templates(
        matches=lambda t: str(t.name).strip() == template_name
    )
    return templates[0] if templates else None


def _field(tpl: Template, name: str, default: Optional[str] = None) -> Optional[str]:
    return str(tpl.get(name).value).strip() if tpl.has(name) else default


def extract_leading_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    match = re.search(r"-?\d+", str(value))
    return int(match.group()) if match else None


def apply_description_override(name: str | None, default: str) -> str:
    if name is None:
        return default
    return DESCRIPTION_OVERRIDES.get(name, default)


def render_wikitext(raw):
    if raw is None or str(raw).strip() == "":
        return ""
    code = mwparserfromhell.parse(str(raw))

    def render_node(node):
        if isinstance(node, Template):
            name = str(node.name).strip().lower()

            def arg(n):
                if not node.has(n):
                    return ""
                value = node.get(n).value
                return (
                    "".join(render_node(child) for child in value.nodes).strip()
                    if hasattr(value, "nodes")
                    else str(value).strip()
                )

            if name == "mult":
                return f"{arg(1)} Mult"
            if name == "chips":
                return f"{arg(1)} Chips"
            if name == "xmult":
                return f"x{arg(1).lstrip('+')} Mult"
            if name in COLOR_DISCARD_TEMPLATES:
                return arg(2)
            if name in IDENTITY_TEMPLATES:
                return arg(1)
            if name in ("sticker", "seal"):
                return arg(1)
            if name == "stake":
                return f"{arg(1)} Stake"
            if name == "money":
                return f"${arg(1)}"
            return arg(1)
        if isinstance(node, Wikilink):
            inner = node.text if node.text else node.title
            return (
                "".join(render_node(n) for n in inner.nodes)
                if hasattr(inner, "nodes")
                else str(inner)
            )
        if isinstance(node, Tag):
            tag_name = str(node.tag).lower()
            if tag_name == "br":
                return " "
            contents = node.contents
            inner = (
                "".join(render_node(n) for n in contents.nodes)
                if hasattr(contents, "nodes")
                else (str(contents) if contents else "")
            )
            if tag_name == "small":
                inner = inner.strip()
                return f"<small>{inner}</small>" if inner else ""
            return inner
        if isinstance(node, (Comment, HTMLEntity)):
            return ""
        return str(node)

    text = "".join(render_node(n) for n in code.nodes)
    text = re.sub(r"[ \t]+", " ", text).strip()
    text = _strip_trailing_running_display(text)
    text = _strip_placeholder_brackets(text)
    text = _strip_pixel_size_tokens(text)
    return text


_TRAILING_DISPLAY_RE = re.compile(
    r"\s+(?:x[\d.]+\s*Mult|[+-]?\d+\s*Mult|[+-]?\d+\s*Chips|[+-]?\d+)\s*$",
    re.IGNORECASE,
)
_BRACKET_PLACEHOLDER_RE = re.compile(r"\[([^\]\n]+)\]")
_PIXEL_TOKEN_RE = re.compile(r"\b\d+px\b")


def _strip_trailing_running_display(text: str) -> str:
    return _TRAILING_DISPLAY_RE.sub("", text)


def _strip_placeholder_brackets(text: str) -> str:
    return _BRACKET_PLACEHOLDER_RE.sub("", text)


def _strip_pixel_size_tokens(text: str) -> str:
    return re.sub(r"\s+", " ", _PIXEL_TOKEN_RE.sub("", text)).strip()


# ──────────────────────────────────────────────────────────────────────
# Parsers
# ──────────────────────────────────────────────────────────────────────


def parse_joker(wikitext: str) -> Optional[dict]:
    tpl = _get_template(wikitext, "Joker info")
    if not tpl:
        return None
    buy_raw = _field(tpl, "buyprice")
    buy = extract_leading_int(buy_raw)
    name = _field(tpl, "title")

    # Forzamos el precio de venta de Credit Card a 1
    if name == "Credit Card":
        sell = 1
    else:
        sell_raw = _field(tpl, "sellprice")
        sell = (
            extract_leading_int(sell_raw) if sell_raw else (buy // 2 if buy else None)
        )

    name = _field(tpl, "title")
    description = apply_description_override(
        name, render_wikitext(_field(tpl, "effect"))
    )

    return {
        "type": "joker",
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": name,
        "image_filename": _field(tpl, "image"),
        "negative_image_filename": _field(tpl, "negativeimage"),
        "description": description,
        "rarity": _field(tpl, "rarity"),
        "effect_type": _field(tpl, "type"),
        "activation": _field(tpl, "activation"),
        "buy_price": buy,
        "sell_price": sell,
        "in_shop": "cannot be found in shop" not in (buy_raw or "").lower(),
        "is_copyable": _field(tpl, "compat-copyable") == "1",
        "is_perishable": _field(tpl, "compat-perishable") == "1",
        "is_eternal": _field(tpl, "compat-eternal") == "1",
        "has_negative_variant": bool(_field(tpl, "negativeimage")),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Available from start.")
        ),
    }


def parse_consumable(wikitext: str) -> Optional[dict]:
    """Parsea Tarots, Planets y Spectrals."""
    tpl = _get_template(wikitext, "Consumable info")
    if not tpl:
        return None

    buy_raw = _field(tpl, "buyprice")
    buy = extract_leading_int(buy_raw)
    sell_raw = _field(tpl, "sellprice")
    sell = extract_leading_int(sell_raw) if sell_raw else (buy // 2 if buy else None)

    name = _field(tpl, "title")
    description = apply_description_override(
        name, render_wikitext(_field(tpl, "effect"))
    )

    return {
        "type": (_field(tpl, "type") or "").lower(),
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": name,
        "image_filename": _field(tpl, "image"),
        "description": description,
        "buy_price": buy,
        "sell_price": sell,
        "in_shop": "cannot be found in shop" not in (buy_raw or "").lower(),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Available from start.")
        ),
    }


def parse_deck(wikitext: str) -> Optional[dict]:
    tpl = _get_template(wikitext, "Deck info")
    if not tpl:
        return None
    name = _field(tpl, "title")
    return {
        "type": "deck",
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": name,
        "image_filename": _field(tpl, "image"),
        "description": apply_description_override(
            name, render_wikitext(_field(tpl, "limit"))
        ),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Unlocked from start")
        ),
    }


def parse_voucher(wikitext: str) -> Optional[dict]:
    tpl = _get_template(wikitext, "Voucher info")
    if not tpl:
        return None
    name = _field(tpl, "title")
    return {
        "type": "voucher",
        "item_number": None,
        "name": name,
        "image_filename": _field(tpl, "image"),
        "voucher_tier": _field(tpl, "type"),
        "description": apply_description_override(
            name, render_wikitext(_field(tpl, "effect"))
        ),
        "next_voucher_name": _field(tpl, "next"),
        "unlock_condition": render_wikitext(
            _field(tpl, "unlock", "Available from start.")
        ),
        "buy_price": extract_leading_int(_field(tpl, "buyprice")),
    }


def parse_challenge_deck(wikitext: str) -> Optional[dict]:
    tpl = _get_template(wikitext, "Challenge info")
    if not tpl:
        return None
    name = _field(tpl, "title")

    modifier_text = CHALLENGE_MODIFIER_OVERRIDES.get(
        name, render_wikitext(_field(tpl, "modifier"))
    )

    starter_text = CHALLENGE_STARTER_OVERRIDES.get(name)
    if starter_text is None:
        starter_text = (
            render_wikitext(_field(tpl, "starter")) if _field(tpl, "starter") else None
        )

    banned_text = CHALLENGE_BANNED_OVERRIDES.get(name)
    if banned_text is None:
        banned_text = (
            render_wikitext(_field(tpl, "banned")) if _field(tpl, "banned") else None
        )

    return {
        "type": "challenge_deck",
        "item_number": extract_leading_int(_field(tpl, "number")),
        "name": name,
        "image_filename": None,
        "modifier": modifier_text,
        "starter": starter_text,
        "banned": banned_text,
        "deck_description": (
            render_wikitext(_field(tpl, "deck")) if _field(tpl, "deck") else None
        ),
    }


def parse_booster_packs_page(wikitext: str) -> list[dict]:
    section_match = re.search(
        r"==\s*List of Booster Packs\s*==\s*(\{\|.*?\|\})", wikitext, re.DOTALL
    )
    if not section_match:
        return []
    packs = []
    current_pack_type = None
    for row in section_match.group(1).split("\n|-"):
        if "Image(s)" in row and "Cost" in row:
            continue
        section_header = re.search(r'colspan="4"[^|!]*id="(\w+)\s+Packs"', row)
        if section_header:
            current_pack_type = section_header.group(1)
            continue
        if current_pack_type is None:
            continue
        cells = _split_wikitable_cells(row)
        if len(cells) < 4:
            continue
        pack = _parse_booster_pack_row(cells, current_pack_type)
        if pack:
            packs.append(pack)
    return packs


def _split_wikitable_cells(row: str) -> list[str]:
    cells = []
    current = None
    for line in row.split("\n"):
        line = line.strip()
        if not line or line.startswith("|-") or line.startswith("|}"):
            continue
        if line.startswith("|"):
            if current is not None:
                cells.append("\n".join(current))
            current = [line.lstrip("|").lstrip()]
        elif current is not None:
            current.append(line)
    if current is not None:
        cells.append("\n".join(current))
    return cells


def _parse_booster_pack_row(cells: list[str], pack_type: str) -> Optional[dict]:
    image_cell, cost_cell, size_cell, effect_cell = cells[:4]
    id_match = re.search(r'id="([^"]+)"', image_cell)
    if not id_match:
        return None

    # Limpieza de nombre
    name = id_match.group(1)

    raw_desc = render_wikitext(effect_cell)
    description = apply_description_override(name, raw_desc)

    return {
        "type": "booster_pack",
        "name": name,
        "pack_type": pack_type,
        "size": size_cell.strip(),
        "cost": extract_leading_int(render_wikitext(cost_cell)),
        "sell_price": 0,
        "in_shop": True,
        "description": description,
        "image_filename": (
            re.search(r"\[\[File:([^|\]]+)", image_cell).group(1).strip()
            if re.search(r"\[\[File:([^|\]]+)", image_cell)
            else None
        ),
    }


def parse_stakes_page(wikitext: str) -> list[dict]:
    match = re.search(r"==\s*List of stakes\s*==.*?(\{\|.*?\|\})", wikitext, re.DOTALL)
    if not match:
        return []
    stakes = []
    for row in match.group(1).split("\n|-"):
        if "abbr title" in row or ("Effect" in row and "Unlocks" in row):
            continue
        cells = _split_wikitable_cells(row)
        if len(cells) < 4:
            continue
        stake = _parse_stake_row(cells)
        if stake:
            stakes.append(stake)
    return stakes


def _parse_stake_row(cells: list[str]) -> Optional[dict]:
    stake_order = extract_leading_int(cells[0])
    if stake_order is None:
        return None
    id_match = re.search(r'id="([^"]+)"', cells[1])
    name = id_match.group(1).strip() if id_match else cells[2].strip()
    return {
        "name": name,
        "stake_order": stake_order,
        "color": name.replace(" Stake", "").strip(),
        "image_filename": (
            re.search(r"\[\[File:([^|\]]+)", cells[1]).group(1).strip()
            if re.search(r"\[\[File:([^|\]]+)", cells[1])
            else None
        ),
        "effect_description": render_wikitext(cells[3]),
        "unlocks_deck_name": (
            re.search(r"\{\{[dD]\|([^}|]+)", cells[4]).group(1).strip()
            if len(cells) > 4 and re.search(r"\{\{[dD]\|([^}|]+)", cells[4])
            else None
        ),
    }


def parse_blind(wikitext: str) -> Optional[dict]:
    tpl = _get_template(wikitext, "Blind info")
    if not tpl:
        return None

    name = _field(tpl, "title")
    # Aplicamos override
    description = apply_description_override(
        name, render_wikitext(_field(tpl, "description"))
    )
    score = float(_field(tpl, "score")) if _field(tpl, "score") else None
    return {
        "name": _field(tpl, "title"),
        "image_filename": _field(tpl, "image"),
        "blind_type": _field(tpl, "type", "Boss"),
        "description": description,
        "ante": _field(tpl, "ante"),
        "score_multiplier": score,
        "reward_money": extract_leading_int(_field(tpl, "reward")),
        "matador_compatible": (_field(tpl, "compat-matador") or "yes").strip().lower()
        not in ("no", "0", "false"),
    }


def parse_tag(wikitext: str) -> Optional[dict]:
    tpl = _get_template(wikitext, "Tag info")
    if not tpl:
        return None

    name = _field(tpl, "title")
    # Aplicamos override
    description = apply_description_override(
        name, render_wikitext(_field(tpl, "description"))
    )
    return {
        "name": _field(tpl, "title"),
        "image_filename": _field(tpl, "image"),
        "description": description,
        "ante": _field(tpl, "ante"),
        "unlock_condition": (
            render_wikitext(_field(tpl, "unlock")) if _field(tpl, "unlock") else None
        ),
    }


def parse_card_modifier(wikitext: str) -> Optional[dict]:
    """Parsea una página de Card Modifier con plantilla ``Modifier info``."""
    tpl = _get_template(wikitext, "Modifier info")
    if not tpl:
        return None

    name = _field(tpl, "title")
    # Aplicamos override
    effect = apply_description_override(name, render_wikitext(_field(tpl, "effect")))

    return {
        "name": name,
        "modifier_type": _field(tpl, "type"),
        "effect": effect,
        "image_filename": _field(tpl, "image"),
    }
