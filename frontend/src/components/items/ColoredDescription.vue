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

const props = defineProps({
  text: { type: String, default: "" },
});

// ── Catálogo de poker hands ──────────────────────────────────────────
// Listadas en orden de "más específicas primero" — necesario porque
// "Straight Flush" debe matchear antes que "Straight" o "Flush"
// individualmente. El regex se construye uniendo este array con `|`,
// y el motor de regex se queda con el primer match más a la izquierda.
const POKER_HANDS = [
  "Royal Flush",
  "Straight Flush",
  "Five of a Kind",
  "Flush House",
  "Flush Five",
  "Four of a Kind",
  "Three of a Kind",
  "Full House",
  "Two Pair",
  "High Card",
  "Pair",
  "Flush",
  "Straight",
];

// Convertir el array a una alternativa de regex. Los espacios se
// quedan tal cual; los caracteres especiales de poker hands no
// necesitan escape.
const POKER_HANDS_PATTERN = POKER_HANDS.join("|");

// ── Regex principal de tokenización ─────────────────────────────────
// Un solo split con un regex que captura cualquiera de los patrones
// reconocibles. Los grupos sin nombre se conservan en el output de
// `.split()` cuando se usan paréntesis de captura — ese es el truco
// que nos permite intercalar tokens "raros" con texto plano.
//
// Orden de alternativas: las más específicas primero para evitar
// matches parciales.
const TOKEN_RE = new RegExp(
  [
    // <small>...</small> con contenido — captura no-greedy.
    "<small>[\\s\\S]*?<\\/small>",
    // Poker hands (singular y plural).
    `(?:${POKER_HANDS_PATTERN})s?`,
    // xN Mult: lleva fondo rojo (más específico que +N Mult).
    "x[\\d.]+\\s*Mult",
    // +N Mult / -N Mult / +N-M Mult (range — MISPRINT case).
    "[+-]\\d+(?:-\\d+)?\\s*Mult",
    // +N Chips / -N Chips.
    "[+-]\\d+\\s*Chips",
    // +$N / -$N
    "(?:-\\$|\\$)\\d+",
    // Card types (singular y plural).
    "Tarots?|Planets?|Spectrals?",
    // Suits (singular y plural). Atención: van DESPUÉS de las card
    // types para que la palabra "Spade" no se confunda con "Spectral"
    // (no comparten prefijo, pero queda más claro visualmente).
    "Diamonds?|Hearts?|Spades?|Clubs?",
  ]
    .map((p) => `(${p})`)
    .join("|"),
  "g",
);

// ── Helpers ─────────────────────────────────────────────────────────
function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Identifica el tipo de un token capturado y devuelve la
 * representación HTML correspondiente. Si el token no es reconocible,
 * devuelve `null` y el caller lo trata como texto plano.
 */
function renderToken(token) {
  if (!token) return null;

  // <small>: se renderiza en línea aparte con tipografía más pequeña.
  // El contenido del <small> se escapa para evitar HTML injection.
  const smallMatch = token.match(/^<small>([\s\S]*?)<\/small>$/);
  if (smallMatch) {
    return `<br><span class="ct-small">${escapeHtml(smallMatch[1])}</span>`;
  }

  if (/^x[\d.]+\s*Mult$/.test(token)) {
    return `<span class="ct-xmult">${escapeHtml(token)}</span>`;
  }
  if (/^[+-]\d+(?:-\d+)?\s*Mult$/.test(token)) {
    return `<span class="ct-mult">${escapeHtml(token)}</span>`;
  }
  if (/^[+-]\d+\s*Chips$/.test(token)) {
    return `<span class="ct-chips">${escapeHtml(token)}</span>`;
  }
  if (/^(?:-\$|\$)\d+$/.test(token)) {
    return `<span class="ct-price">${escapeHtml(token)}</span>`;
  }

  // Poker hands: check tras los specifics porque pueden aparecer al
  // final de strings tipo "Royal Flushes" (plural).
  const POKER_HAND_RE = new RegExp(`^(?:${POKER_HANDS_PATTERN})s?$`);
  if (POKER_HAND_RE.test(token)) {
    return `<span class="ct-poker">${escapeHtml(token)}</span>`;
  }

  if (/^Tarots?$/.test(token)) return `<span class="ct-tarot">${token}</span>`;
  if (/^Planets?$/.test(token)) return `<span class="ct-planet">${token}</span>`;
  if (/^Spectrals?$/.test(token)) return `<span class="ct-spectral">${token}</span>`;
  if (/^Diamonds?$/.test(token)) return `<span class="ct-diamond">${token}</span>`;
  if (/^Hearts?$/.test(token)) return `<span class="ct-heart">${token}</span>`;
  if (/^Spades?$/.test(token)) return `<span class="ct-spade">${token}</span>`;
  if (/^Clubs?$/.test(token)) return `<span class="ct-club">${token}</span>`;

  return null;
}

// ── Render principal ────────────────────────────────────────────────
const renderedHtml = computed(() => {
  const raw = props.text || "";
  if (!raw) return "";

  // String.split con un regex con grupos de captura devuelve un array
  // alternando: [texto, match1, match2, ..., texto, match1, ...].
  // Los `match2..N` son `undefined` cuando solo uno de los grupos
  // capturó — los filtramos.
  const parts = raw.split(TOKEN_RE);

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
}

/*
 * Las clases coloreadas se aplican vía v-html, que no propaga el
 * scoped attribute. `:deep()` permite que los selectores penetren a
 * los descendientes sin scope. Sin :deep() los estilos NO se
 * aplicarían (el HTML inyectado no llevaría la marca scoped).
 */
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

/*
 * <small>: línea aparte con tipografía un poco más pequeña.
 * `display: inline-block` con margin-top + 100% width simula un
 * párrafo separado sin requerir un wrapper <p> aparte.
 *
 * Opacity ligeramente reducida para que se perciba "secundario"
 * respecto al texto principal sin esconderlo.
 */
:deep(.ct-small) {
  display: inline-block;
  width: 100%;
  margin-top: 6px;
  font-size: 0.88em;
  opacity: 0.82;
  line-height: 1.4;
}
</style>
