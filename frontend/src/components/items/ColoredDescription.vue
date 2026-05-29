<!--
  Renderizador de descripciones con syntax-highlight.

  Recibe el texto plano que sale del backend (ya limpio de wikitext
  por `render_wikitext`) y lo tokeniza para aplicar color y formato a
  patrones reconocibles:

    +N Chips / -N Chips         → azul (#0093FF)
    +N Mult / -N Mult           → rojo (#FF4C40)
    +N-M Mult (MISPRINT)        → rojo (mismo color que +N Mult)
    xN Mult                     → fondo rojo (#FF4C40), texto blanco
    Royal Flush, Pair, etc.     → naranja (#FF8F00)
    Tarot / Tarots              → púrpura (#CA8CFF)
    Planet / Planets            → celeste (#69E6FF)
    Spectral / Spectrals        → azul (#76A6FF)
    Diamond / Diamonds          → naranja (#FFA300)
    Heart / Hearts              → rojo (#F83B2F)
    Spade / Spades              → gris azulado (#8FB1B8)
    Club / Clubs                → azul cyan (#009CFD)
    <small>...</small>          → línea aparte + tipografía más pequeña

  La separación de responsabilidades es deliberada:

    - Backend (`render_wikitext`) → texto plano + markers semánticos
      mínimos (`<small>`). NO añade color HTML.
    - Frontend (este componente) → tokenización + aplicación de
      estilos visuales.

  Por qué aquí y no en CSS global: el regex de tokenización tiene que
  preservar el orden de los tokens y NO matchear patrones dentro de
  palabras (e.g. "Flush" dentro de "Flushing"). Eso requiere lógica JS,
  no CSS. Y para no duplicarla entre ItemDetailPanel e ItemTooltip,
  vive en un solo componente compartido.

  Implementación: split + clasificación + render con v-html. El
  contenido del usuario (texto del wiki) se escapa via `escapeHtml`
  antes de meterlo en innerHTML — no hay XSS aunque el wiki cambie.
-->
<template>
  <span class="colored-desc" v-html="renderedHtml" />
</template>

<script setup>
import { computed } from "vue";
import { useDictionaryStore } from "@/stores/dictionary";

const props = defineProps({
  text: { type: String, default: "" },
});

const dictStore = useDictionaryStore();

const POKER_HANDS = [
  "Royal Flush",
  "Royal Flushes",
  "Straight Flush",
  "Straight Flushes",
  "Five of a Kind",
  "Fives of a Kind",
  "Flush House",
  "Flush Houses",
  "Flush Five",
  "Flush Fives",
  "Four of a Kind",
  "Fours of a Kind",
  "Three of a Kind",
  "Threes of a Kind",
  "Full House",
  "Full Houses",
  "Two Pair",
  "Two Pairs",
  "High Card",
  "High Cards",
  "Pair",
  "Pairs",
  "Flush",
  "Flushes",
  "Straight",
  "Straights",
];

// Ordenamos de más largo a más corto para que los plurales tengan prioridad
const POKER_HANDS_PATTERN = [...POKER_HANDS].sort((a, b) => b.length - a.length).join("|");

// Regex dinámico reactivo: Se actualiza solo si el diccionario recibe palabras nuevas
const dynamicTokenRe = computed(() => {
  const patterns = ["<small>[\\s\\S]*?<\\/small>"];

  // El diccionario va ANTES que las palabras genéricas.
  // Así, "Planet Merchant" se detecta entero antes de que la regla "Planets?"
  // divida la frase y se quede solo con la primera palabra.
  if (dictStore.itemNamesPattern) {
    patterns.push(`(?:${dictStore.itemNamesPattern})s?`);
  }

  // Bypass específico para la palabra "Joker" aislada en Five-Card Draw.
  // Como lo guardamos en memoria pero no en el Regex global, esto lo activa.
  if (props.text && props.text.includes("Card Sharp") && props.text.includes("Joker")) {
    patterns.push("\\bJoker\\b");
  }

  // Resto de reglas genéricas de colores
  patterns.push(
    `(?:${POKER_HANDS_PATTERN})`,
    "x[\\d.]+\\s*Mult",
    "[+-]\\d+(?:-\\d+)?\\s*Mult",
    "[+-]\\d+\\s*Chips",
    "(?:-\\$|\\$)\\d+",
    "Tarots?|Planets?|Spectrals?",
    "Diamonds?|Hearts?|Spades?|Clubs?",
  );

  // La bandera 'ig' (Case-Insensitive) permite detectar "vampire" aunque el usuario escriba "Vampire"
  return new RegExp("(" + patterns.map((p) => `(?:${p})`).join("|") + ")", "ig");
});

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderToken(token) {
  if (!token) return null;

  const smallMatch = token.match(/^<small>([\s\S]*?)<\/small>$/i);
  if (smallMatch) return `<br><span class="ct-small">${escapeHtml(smallMatch[1])}</span>`;

  if (/^x[\d.]+\s*Mult$/i.test(token)) return `<span class="ct-xmult">${escapeHtml(token)}</span>`;
  if (/^[+-]\d+(?:-\d+)?\s*Mult$/i.test(token))
    return `<span class="ct-mult">${escapeHtml(token)}</span>`;
  if (/^[+-]\d+\s*Chips$/i.test(token)) return `<span class="ct-chips">${escapeHtml(token)}</span>`;
  if (/^(?:-\$|\$)\d+$/i.test(token)) return `<span class="ct-price">${escapeHtml(token)}</span>`;

  const POKER_HAND_RE = new RegExp(`^(?:${POKER_HANDS_PATTERN})$`, "i");
  if (POKER_HAND_RE.test(token)) return `<span class="ct-poker">${escapeHtml(token)}</span>`;

  if (/^Tarots?$/i.test(token)) return `<span class="ct-tarot">${token}</span>`;
  if (/^Planets?$/i.test(token)) return `<span class="ct-planet">${token}</span>`;
  if (/^Spectrals?$/i.test(token)) return `<span class="ct-spectral">${token}</span>`;
  if (/^Diamonds?$/i.test(token)) return `<span class="ct-diamond">${token}</span>`;
  if (/^Hearts?$/i.test(token)) return `<span class="ct-heart">${token}</span>`;
  if (/^Spades?$/i.test(token)) return `<span class="ct-spade">${token}</span>`;
  if (/^Clubs?$/i.test(token)) return `<span class="ct-club">${token}</span>`;

  // Magia del diccionario: si detecta una carta registrada, saca la imagen
  const imgUrl = dictStore.getImage(token);
  if (imgUrl) {
    return `<span class="ct-item-name"><img src="${imgUrl}" class="ct-item-icon" />${escapeHtml(token)}</span>`;
  }

  return null;
}

const renderedHtml = computed(() => {
  const raw = props.text || "";
  if (!raw) return "";

  const parts = raw.split(dynamicTokenRe.value);
  let html = "";
  for (const part of parts) {
    if (part === undefined || part === "") continue;
    const rendered = renderToken(part);
    if (rendered !== null) {
      html += rendered;
    } else {
      html += escapeHtml(part);
    }
  }
  return html;
});
</script>

<style lang="scss" scoped>
.colored-desc {
  display: inline;
  font-size: 14px;
}

/* Clases coloreadas existentes */
:deep(.ct-xmult) {
  background: #ff4c40;
  color: #fff;
  padding: 1px 5px;
  border-radius: 2px;
  font-weight: 700;
}
:deep(.ct-mult) {
  color: #ff4c40;
  font-weight: 700;
}
:deep(.ct-chips) {
  color: #0093ff;
  font-weight: 700;
}
:deep(.ct-poker) {
  color: #ff8f00;
  font-weight: 700;
}
:deep(.ct-tarot) {
  color: #ca8cff;
  font-weight: 700;
}
:deep(.ct-planet) {
  color: #69e6ff;
  font-weight: 700;
}
:deep(.ct-spectral) {
  color: #76a6ff;
  font-weight: 700;
}
:deep(.ct-diamond) {
  color: #ffa300;
  font-weight: 700;
}
:deep(.ct-heart) {
  color: #f83b2f;
  font-weight: 700;
}
:deep(.ct-spade) {
  color: #8fb1b8;
  font-weight: 700;
}
:deep(.ct-club) {
  color: #009cfd;
  font-weight: 700;
}
:deep(.ct-price) {
  color: #f5b244;
  font-weight: 700;
}

:deep(.ct-small) {
  display: inline-block;
  width: 100%;
  margin-top: 6px;
  font-size: 0.88em;
  opacity: 0.82;
  line-height: 1.4;
}

/* --- NUEVAS CLASES PARA ITEMS DEL DICCIONARIO --- */
:deep(.ct-item-name) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #fcfcfc; /* Un blanco más nítido para resaltar el ítem */
  vertical-align: middle;
  background: rgba(0, 0, 0, 0.25);
  padding: 2px 8px;
  border-radius: 6px;
  margin: 2px 0;
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.1);
}

:deep(.ct-item-icon) {
  width: 18px;
  height: 18px;
  object-fit: contain;
  image-rendering: pixelated;
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.6));
}
</style>
