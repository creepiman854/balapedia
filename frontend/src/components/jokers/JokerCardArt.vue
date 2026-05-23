<!--
  Renderiza la "carta" de un joker — SIN frame SVG decorativo a su
  alrededor. La carta queda suelta sobre el grid, igual que en el
  juego real (ver imagen de referencia).

  Tres modos visuales:
    1. `image_url` y no bloqueado → <img> a pelo, ratio carta de Balatro.
    2. No `image_url` y no bloqueado → carta blanca con letra inicial
       generada deterministícamente desde el nombre (fallback estético).
    3. Bloqueado → "card back" genérico oscuro con "?" centrado.

  El componente NO impone un tamaño fijo: ocupa el 100% del slot que
  le dé el padre. El padre (JokerCard) controla el sizing vía
  aspect-ratio en su wrapper.
-->
<template>
  <!-- Bloqueado: dorso genérico de carta -->
  <div v-if="isLocked" class="card-back" aria-label="Joker bloqueado">
    <span class="card-back__q">?</span>
  </div>

  <!-- Con imagen: la carta tal cual, sin frame -->
  <img
    v-else-if="joker.image_url"
    :src="joker.image_url"
    :alt="joker.name"
    class="card-img"
    draggable="false"
    loading="lazy"
  />

  <!-- Fallback sin imagen: carta blanca con letra generada -->
  <div
    v-else
    class="card-fallback"
    :style="{
      background: `linear-gradient(165deg, hsl(${hue}, 28%, 96%), hsl(${hue}, 35%, 88%))`,
    }"
  >
    <span class="card-fallback__sym" :style="{ color: `hsl(${hue}, 70%, 32%)` }">
      {{ sym }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  joker: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
})

/**
 * Hue determinístico desde el nombre — mismo joker, mismo color en
 * cada render, sin parpadeo al recargar.
 */
function nameHue(name) {
  if (!name) return 200
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360
  return h
}

const hue = computed(() => nameHue(props.joker.name))
const sym = computed(() => (props.joker.name || '?').trim()[0]?.toUpperCase() || '?')
</script>

<style lang="scss" scoped>
/*
 * Las tres variantes comparten el mismo box: 100% del slot, aspect-ratio
 * de carta Balatro (71:95 aprox), border-radius suave para que NO
 * desentonen con el sistema pixel del resto pero sigan pareciendo cartas
 * sueltas.
 */
.card-img,
.card-back,
.card-fallback {
  width: 100%;
  display: block;
  aspect-ratio: 71 / 95;
  border-radius: 8px;
  user-select: none;
  image-rendering: pixelated;
}

.card-img {
  object-fit: cover;
  background: transparent;
}

.card-back {
  background: linear-gradient(160deg, #1a2a2e 0%, #0d1517 100%);
  border: 2px solid #3a5055;
  display: flex;
  align-items: center;
  justify-content: center;

  &__q {
    font-family: 'm6x11plus', monospace;
    font-size: 38%;          /* relativo al ancho del card vía cQ no funciona en todos los navegadores; usamos % del font-size base */
    font-size: clamp(28px, 4vw, 64px);
    color: #4d6870;
    text-shadow: 0 2px 0 rgba(0, 0, 0, 0.5);
  }
}

.card-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(0, 0, 0, 0.15);
  box-shadow: inset 0 0 0 4px #fff;

  &__sym {
    font-family: 'm6x11plus', monospace;
    font-size: clamp(28px, 5vw, 80px);
    text-shadow: 0 2px 0 rgba(0, 0, 0, 0.18);
  }
}
</style>
