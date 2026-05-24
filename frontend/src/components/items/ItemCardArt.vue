<!--
  Render de la "carta" de un item del catálogo (joker, consumible, etc.).

  Modos:
    1. `image_url` y no bloqueado → <img> con drop-shadow CSS aplicado
       directamente sobre la imagen. Esto sí respeta el alpha del PNG
       (jokers no rectangulares, consumibles con borde transparente, …)
       — el shadow se "recorta" siguiendo la silueta de la carta y NO
       genera un halo de rectángulo bounding box.
    2. Sin `image_url` → carta blanca con letra inicial generada
       deterministícamente del nombre. Sirve mientras el backend no
       pueble image_url.
    3. Bloqueado → "card back" oscuro con "?" centrado.

  Sin <svg> wrapper, sin marco de rareza — la carta vive suelta.

  Trade-off: `filter: drop-shadow` crea una capa de compositing GPU por
  card. Con ~150 jokers visibles, son ~150 capas extra. Firefox lo
  asume mejor que en pases anteriores gracias a la combinación de
  rAF-throttled tilt + will-change en el wrapper.
-->
<template>
  <!-- Bloqueado: dorso genérico de carta -->
  <div v-if="isLocked" class="card-back" :style="shadowStyle" aria-label="Item bloqueado">
    <span class="card-back__q">?</span>
  </div>

  <!-- Con imagen: la carta tal cual, sin frame -->
  <img
    v-else-if="item.image_url"
    :src="item.image_url"
    :alt="item.name"
    class="card-img"
    :style="shadowStyle"
    draggable="false"
    loading="lazy"
  />

  <!-- Fallback sin imagen: carta blanca con letra generada -->
  <div
    v-else
    class="card-fallback"
    :style="fallbackStyle"
  >
    <span class="card-fallback__sym" :style="{ color: `hsl(${hue}, 70%, 32%)` }">
      {{ sym }}
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  item: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false },
  /**
   * Accent visual del item (rareza para jokers, type para consumibles).
   * Lo recibe del padre via `getItemAccent(item)`.
   */
  accent: {
    type: Object,
    default: () => ({ color: '#708387', glow: 'rgba(112,131,135,0.4)' }),
  },
})

function nameHue(name) {
  if (!name) return 200
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360
  return h
}

const hue = computed(() => nameHue(props.item.name))
const sym = computed(() => (props.item.name || '?').trim()[0]?.toUpperCase() || '?')

/**
 * Drop-shadow alpha-aware aplicado a la imagen. Cuando la carta está
 * seleccionada, dos drop-shadows: uno de color del accent (glow
 * intenso) + uno negro detrás. Cuando no, solo el shadow neutro.
 */
const shadowFilter = computed(() => {
  if (props.isSelected) {
    return `drop-shadow(0 0 14px ${props.accent.color}) drop-shadow(0 6px 14px rgba(0,0,0,0.9))`
  }
  return 'drop-shadow(0 4px 8px rgba(0,0,0,0.55))'
})

const shadowStyle = computed(() => ({ filter: shadowFilter.value }))

const fallbackStyle = computed(() => ({
  background: `linear-gradient(165deg, hsl(${hue.value}, 28%, 96%), hsl(${hue.value}, 35%, 88%))`,
  filter: shadowFilter.value,
}))
</script>

<style lang="scss" scoped>
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
  object-fit: contain;
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
