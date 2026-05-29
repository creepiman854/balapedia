<!--
  Render de la "carta" de un item del catálogo (joker, consumable, etc.).

  Modos (resolución por orden de precedencia):
    1. Bloqueado + modo spoiler ON + tiene image_url → muestra la
       imagen real con desaturación + brillo reducido. El usuario
       eligió revelar los locked en Ajustes.
    2. Bloqueado + locked_image_url disponible (Joker/Voucher/Deck) →
       muestra el asset oficial "locked" de la wiki.
    3. Bloqueado sin asset oficial (Consumable/Pack/Challenge) →
       fallback al dorso genérico "card-back" oscuro con "?".
    4. Desbloqueado + image_url → <img> con drop-shadow CSS aplicado
       directamente sobre la imagen.
    5. Desbloqueado, sin image_url propia pero CHALLENGE_DECK → usamos
       el asset representativo compartido de Challenge Decks.
    6. Desbloqueado sin image_url → carta blanca con letra inicial.

  Sin <svg> wrapper, sin marco de rareza — la carta vive suelta.
-->
<template>
  <!-- Modo 1: Bloqueado + spoiler ON + tiene imagen real → revelado atenuado -->
  <img
    v-if="isSpoiledRender"
    :src="item.image_url || CHALLENGE_DECK_FALLBACK_IMAGE"
    :alt="item.name"
    class="card-img card-img--spoiled"
    :style="shadowStyle"
    draggable="false"
    loading="lazy"
  />

  <!-- Modo 2: Bloqueado + locked_image_url oficial → asset locked de la wiki -->
  <img
    v-else-if="isLocked && item.locked_image_url"
    :src="item.locked_image_url"
    :alt="`${item.name} locked`"
    class="card-img card-img--locked"
    :style="shadowStyle"
    draggable="false"
    loading="lazy"
  />

  <!-- Modo 3: Bloqueado sin asset oficial → dorso genérico "?" -->
  <div v-else-if="isLocked" class="card-back" :style="shadowStyle" aria-label="Locked item">
    <span class="card-back__q">?</span>
  </div>

  <!-- Modo 4: Desbloqueado + imagen → carta tal cual, sin frame -->
  <img
    v-else-if="item.image_url"
    :src="item.image_url"
    :alt="item.name"
    class="card-img"
    :style="shadowStyle"
    draggable="false"
    loading="lazy"
  />

  <!-- Modo 5: Challenge Deck sin imagen propia → asset compartido -->
  <img
    v-else-if="isChallengeDeck"
    :src="CHALLENGE_DECK_FALLBACK_IMAGE"
    :alt="item.name"
    class="card-img card-img--challenge"
    :style="shadowStyle"
    draggable="false"
    loading="lazy"
  />

  <!-- Modo 6: Fallback sin imagen → carta blanca con letra generada -->
  <div v-else class="card-fallback" :style="fallbackStyle">
    <span class="card-fallback__sym" :style="{ color: `hsl(${hue}, 70%, 32%)` }">
      {{ sym }}
    </span>
  </div>

  <!-- NUEVO: Overlay identificativo para Challenge Decks -->
  <!-- Solo se muestra si es un reto y (está desbloqueado O el usuario tiene el spoiler activo) -->
  <div v-if="isChallengeDeck && (!isLocked || isSpoiledRender)" class="challenge-name-overlay">
    <span class="challenge-name-text">{{ item.name }}</span>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useSettingsStore } from "@/stores/settings";

const CHALLENGE_DECK_FALLBACK_IMAGE = "https://balatrowiki.org/images/Challenge_Deck.png";

const props = defineProps({
  item: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false },
  accent: {
    type: Object,
    default: () => ({ color: "#708387", glow: "rgba(112,131,135,0.4)" }),
  },
});

const settings = useSettingsStore();
const { showSpoiledLocked } = storeToRefs(settings);

function nameHue(name) {
  if (!name) return 200;
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360;
  return h;
}

const hue = computed(() => nameHue(props.item.name));
const sym = computed(() => (props.item.name || "?").trim()[0]?.toUpperCase() || "?");

const isChallengeDeck = computed(
  () => String(props.item?.type || "").toUpperCase() === "CHALLENGE_DECK",
);

const isSpoiledRender = computed(
  () =>
    props.isLocked && showSpoiledLocked.value && (!!props.item?.image_url || isChallengeDeck.value),
);

const shadowFilter = computed(() => {
  const parts = [];
  if (isSpoiledRender.value) {
    parts.push("grayscale(0.85)", "brightness(0.55)", "contrast(0.95)");
  } else if (props.isLocked && props.item?.locked_image_url) {
    parts.push("brightness(0.65)");
  }

  if (props.isSelected) {
    parts.push(`drop-shadow(0 0 14px ${props.accent.color})`);
    parts.push("drop-shadow(0 6px 14px rgba(0,0,0,0.9))");
  } else {
    parts.push("drop-shadow(0 4px 8px rgba(0,0,0,0.55))");
  }
  return parts.join(" ");
});

const shadowStyle = computed(() => ({ filter: shadowFilter.value }));

const fallbackStyle = computed(() => ({
  background: `linear-gradient(165deg, hsl(${hue.value}, 28%, 96%), hsl(${hue.value}, 35%, 88%))`,
  filter: shadowFilter.value,
}));
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

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

/* Hooks para variantes */
.card-img--spoiled,
.card-img--locked,
.card-img--challenge {
  transition: filter 0.2s ease;
}

.card-back {
  background: linear-gradient(160deg, #1a2a2e 0%, #0d1517 100%);
  border: 2px solid #3a5055;
  display: flex;
  align-items: center;
  justify-content: center;

  &__q {
    font-family: "m6x11plus", monospace;
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
    font-family: "m6x11plus", monospace;
    font-size: clamp(28px, 5vw, 80px);
    text-shadow: 0 2px 0 rgba(0, 0, 0, 0.18);
  }
}

/* --- OVERLAY DE CHALLENGE DECKS --- */
.challenge-name-overlay {
  position: absolute;
  inset: 0;

  display: flex;
  align-items: flex-end;
  justify-content: center;

  padding-bottom: 12px;

  pointer-events: none;
  z-index: 5;
}

.challenge-name-text {
  position: relative;

  max-width: 82%;

  padding: 6px 12px;

  font-family: "m6x11plus", monospace;
  font-size: 16px;
  line-height: 1;
  letter-spacing: 0.4px;
  text-align: center;
  color: #f3f4f6;

  /*
   * Mucho más limpio y discreto.
   * Parece una pequeña placa informativa
   * integrada sobre la carta.
   */
  background: rgba(16, 18, 24, 0.82);

  /*
   * Borde pixelado.
   */
  @include pixel-clip;

  border: 1px solid rgba(255, 255, 255, 0.08);

  /*
   * Profundidad sutil.
   */
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);

  /*
   * Mucho menos agresivo visualmente.
   */
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.9);

  /*
   * Evita que nombres largos rompan el layout.
   */
  overflow-wrap: break-word;

  /*
   * Ligero blur de fondo para separar del arte
   * sin necesidad de colores fuertes.
   */
  backdrop-filter: blur(2px);
}
</style>
