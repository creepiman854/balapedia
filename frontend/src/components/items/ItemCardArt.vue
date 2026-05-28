<!--
  Render de la "carta" de un item del catálogo (joker, consumible, etc.).

  Modos (resolución por orden de precedencia):
    1. Bloqueado + modo spoiler ON + tiene image_url → muestra la
       imagen real con desaturación + brillo reducido. El usuario
       eligió revelar los locked en Ajustes.
    2. Bloqueado + locked_image_url disponible (Joker/Voucher/Deck) →
       muestra el asset oficial "locked" de la wiki.
    3. Bloqueado sin asset oficial (Consumable/Pack/Challenge) →
       fallback al dorso genérico "card-back" oscuro con "?".
    4. Desbloqueado + image_url → <img> con drop-shadow CSS aplicado
       directamente sobre la imagen. Esto respeta el alpha del PNG
       (jokers no rectangulares, consumibles con borde transparente, …)
       — el shadow se "recorta" siguiendo la silueta de la carta y NO
       genera un halo de rectángulo bounding box.
    5. Desbloqueado sin image_url → carta blanca con letra inicial
       generada deterministícamente del nombre. Sirve mientras el
       backend no pueble image_url.

  Sin <svg> wrapper, sin marco de rareza — la carta vive suelta.

  Trade-off: `filter: drop-shadow` crea una capa de compositing GPU por
  card. Con ~150 jokers visibles, son ~150 capas extra. Firefox lo
  asume mejor que en pases anteriores gracias a la combinación de
  rAF-throttled tilt + will-change en el wrapper.

  El modo spoiler vive en `settings.showSpoiledLocked` (Pinia). Default
  OFF — el usuario tiene que ir a Ajustes a activarlo. Solo afecta a
  Jokers/Vouchers/Decks (los demás tipos no tienen estado bloqueado
  visible en el grid).

  Implementación del filtro: el desaturado/atenuado del modo spoiler se
  añade DENTRO de la misma string CSS `filter:` que el drop-shadow,
  porque el style inline siempre gana sobre las reglas externas. Si lo
  pusiéramos en una clase, el `:style="shadowStyle"` la anularía.
-->
<template>
  <!-- Modo 1: Bloqueado + spoiler ON + tiene imagen real → revelado atenuado -->
  <img
    v-if="isLocked && showSpoiledLocked && item.image_url"
    :src="item.image_url"
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
    :alt="`${item.name} bloqueado`"
    class="card-img card-img--locked"
    :style="shadowStyle"
    draggable="false"
    loading="lazy"
  />

  <!-- Modo 3: Bloqueado sin asset oficial → dorso genérico "?" -->
  <div v-else-if="isLocked" class="card-back" :style="shadowStyle" aria-label="Item bloqueado">
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

  <!-- Modo 5: Fallback sin imagen → carta blanca con letra generada -->
  <div v-else class="card-fallback" :style="fallbackStyle">
    <span class="card-fallback__sym" :style="{ color: `hsl(${hue}, 70%, 32%)` }">
      {{ sym }}
    </span>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useSettingsStore } from "@/stores/settings";

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
    default: () => ({ color: "#708387", glow: "rgba(112,131,135,0.4)" }),
  },
});

// Toggle global del modo "spoiler" para items bloqueados.
// Vive en el store de settings con persistencia en localStorage.
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

/**
 * Caso espacial activo cuando el item está bloqueado, el usuario tiene
 * activado el modo spoiler en Ajustes, y la carta tiene una imagen
 * real que mostrar atenuada. Encapsulado para no repetir la condición
 * en plantilla y filter.
 */
const isSpoiledRender = computed(
  () => props.isLocked && showSpoiledLocked.value && !!props.item?.image_url,
);

/**
 * Filtro CSS aplicado a la <img> / card-back / fallback.
 *
 * El shadow base (selected vs no-selected) siempre va. Si la carta se
 * renderiza en modo spoiler, ENCABEZAMOS la string con grayscale +
 * brightness + contrast — el orden importa: los filtros se componen
 * en secuencia, así que primero desaturamos/atenuamos los colores y
 * después aplicamos el drop-shadow sobre el resultado atenuado (el
 * shadow recoge el alpha real de la PNG, no se altera por el filtro
 * de color anterior).
 *
 * Decidimos construirlo aquí en lugar de en una clase CSS para que
 * el style inline (`:style="shadowStyle"`) gane sobre cualquier regla
 * externa — los style inline siempre tienen mayor specificity.
 */
const shadowFilter = computed(() => {
  const parts = [];

  if (isSpoiledRender.value) {
    // Modo 1: Revelado atenuado (Modo Spoiler)
    parts.push("grayscale(0.85)", "brightness(0.55)", "contrast(0.95)");
  } else if (props.isLocked && props.item?.locked_image_url) {
    // Modo 2: Asset oficial bloqueado (sin spoiler)
    parts.push("brightness(0.65)");
  }

  // Las sombras se aplican siempre al final de la cadena
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

/*
 * Variante "spoiler" (image_url real atenuada) y "locked" (asset
 * oficial de la wiki) heredan todo del .card-img base. La distinción
 * vive solo en el src y en el computed `shadowFilter` (que añade los
 * filtros de desaturado/brillo cuando aplica). Mantengo las clases
 * para que sea trivial localizarlas con DevTools y para hooks
 * futuros (e.g. animar `transition: filter 0.2s ease` al cambiar
 * el toggle de spoiler).
 */
.card-img--spoiled,
.card-img--locked {
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
</style>
