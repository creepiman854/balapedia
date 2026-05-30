<!--
  Wrapper interactivo de una carta de item en el grid.

  Doble wrapper:
    .arch       → posición base + z-index (arco + selected + stack)
    .tilt-wrap  → tilt+zoom on hover (v-tilt)

  Shadow: lo aplica ItemCardArt sobre la <img> (alpha-aware).

  Prop `stack`: cuando true, dibuja 2 sombras detrás de la carta
  simulando un mazo. Pensado para la sub-vista MAZOS. Las sombras
  viven en .arch (no en .tilt-wrap), así no rotan con el tilt — solo
  la carta de arriba se inclina, las de "debajo" se quedan quietas.
-->
<template>
  <div
    class="arch"
    :class="{
      'arch--selected': isSelected,
      'arch--gold': isGold,
    }"
    :style="archStyle"
  >
    <template v-if="stack">
      <!-- Cambiamos isLocked por realLockStatus -->
      <div
        class="deck-shadow deck-shadow--back"
        :class="{ 'deck-shadow--locked': isActuallyLocked }"
      />
      <div
        class="deck-shadow deck-shadow--mid"
        :class="{ 'deck-shadow--locked': isActuallyLocked }"
      />
    </template>
    <div
      v-tilt="{ max: 18, scale: 1.07, speed: 320 }"
      class="tilt-wrap"
      @click="emit('select', item)"
      @mouseenter="onEnter"
      @mouseleave="emit('leave')"
    >
      <div class="art-container-wrapper">
        <transition name="reveal-pop" mode="out-in">
          <div class="art-container" :key="isLocked">
            <ItemCardArt
              :item="item"
              :is-locked="isLocked"
              :is-selected="isSelected"
              :accent="accent"
            />
          </div>
        </transition>
      </div>
      <!-- Sticker overlay -->
      <transition
        :name="
          itemType === 'CHALLENGE_DECK'
            ? 'check-pop'
            : itemType === 'JOKER'
              ? 'sticker-apply'
              : 'stake-drop'
        "
        mode="out-in"
      >
        <iconify-icon
          v-if="!isLocked && itemType === 'CHALLENGE_DECK' && item.highest_stake_order === 1"
          icon="pixel:check-circle-solid"
          class="challenge-check-overlay"
          noobserver
        />
        <img
          v-else-if="!isLocked && stickerOverlay?.image_url && itemType !== 'CHALLENGE_DECK'"
          :key="stickerOverlay.image_url"
          :src="stickerOverlay.image_url"
          class="sticker-overlay"
          :class="itemType === 'JOKER' ? 'sticker-overlay--joker' : 'sticker-overlay--deck'"
          draggable="false"
        />
      </transition>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { getItemAccent } from "@/constants/items";
import ItemCardArt from "./ItemCardArt.vue";
import { useProgressionStore } from "@/stores/progression";

const props = defineProps({
  item: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false },
  colIndex: { type: Number, default: 0 },
  colCount: { type: Number, default: 1 },
  /** Renderiza el efecto "pila de cartas" detrás. Para MAZOS. */
  stack: { type: Boolean, default: false },
});

const emit = defineEmits(["select", "hover", "leave"]);

const accent = computed(() => getItemAccent(props.item));
const itemType = computed(() => String(props.item?.type || "").toUpperCase());

const archStyle = computed(() => {
  const base = props.isSelected ? 5 : 1;
  if (props.colCount < 2) return { zIndex: base };
  const half = (props.colCount - 1) / 2;
  const norm = (props.colIndex - half) / half;
  const dropY = norm * norm * 16;
  const rotZ = norm * 3.5;
  return {
    transform: `translateY(${dropY.toFixed(2)}px) rotate(${rotZ.toFixed(2)}deg)`,
    zIndex: base,
  };
});

function onEnter(e) {
  emit("hover", { item: props.item, target: e.currentTarget });
}

const isActuallyLocked = computed(() => {
  /*
   * Estado REAL del unlock.
   * NO depende del toggle de mostrar cartas bloqueadas.
   */
  if ("unlocked_for_me" in props.item) {
    return !props.item.unlocked_for_me;
  }

  return props.isLocked;
});

const progStore = useProgressionStore();

const stickerOverlay = computed(() => {
  if (!props.item?.highest_stake_order) return null;
  const type = String(props.item.type || "").toUpperCase();
  return progStore.getProgressionInfo(props.item.highest_stake_order, type);
});

const isGold = computed(() => props.item?.highest_stake_order === 8);
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.arch {
  width: 100%;
  display: block;
  position: relative;
  transition: transform 0.25s ease;

  &:hover {
    z-index: 10 !important;
  }
}

.arch--selected {
  z-index: 5;
}

.tilt-wrap {
  width: 100%;
  display: block;
  cursor: pointer;
  position: relative;

  /* La carta SIEMPRE encima de las sombras */
  z-index: 1;
}

/*
 * Stack visual del mazo
 */
.deck-shadow {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  aspect-ratio: 71 / 95;
  border-radius: 8px;
  @include pixel-clip;

  /*
   * Locked → estilo oscuro actual
   * Unlocked → blanco tipo carta real
   */
  background: linear-gradient(160deg, #fdfdfd 0%, #ececec 100%);
  border: 1px solid rgba(255, 255, 255, 0.85);

  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.35);

  pointer-events: none;

  /* MUY IMPORTANTE */
  z-index: 0;

  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

/* Estado LOCKED → vuelve al look oscuro */
.deck-shadow--locked {
  background: linear-gradient(160deg, #e5e5e5 0%, #b5b5b5 100%);
  border: 1px solid rgba(120, 120, 120, 0.4);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.deck-shadow--back {
  transform: translate(4px, 4px) rotate(-1deg);
}

.deck-shadow--mid {
  transform: translate(2px, 2px) rotate(0.5deg);
}

.sticker-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  image-rendering: pixelated;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.4));
  z-index: 2;

  /* Reset de propiedades base para que los modificadores tengan control total */
  object-fit: contain;
}

/* Comportamiento específico para Stickers de Jokers */
.sticker-overlay--joker {
  /* Al usar cover + top right, forzamos que se vea el sticker de arriba a la derecha */
  object-fit: cover !important;
  object-position: top right;
  transform-origin: top right;
}

/* Comportamiento específico para Stakes de Mazos */
.sticker-overlay--deck {
  /* El contain por defecto del padre es perfecto para stakes */
  object-fit: contain !important;
  padding: 10%;
  object-position: bottom right;
  transform-origin: bottom right;
  transform: scale(0.4);
}

.arch--gold {
  .tilt-wrap {
    filter: drop-shadow(0 0 6px #f0a020) drop-shadow(0 0 12px rgba(240, 160, 32, 0.3));
  }
}

/* Checkmark de Challenge Decks completados */
.challenge-check-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  bottom: auto;
  left: auto;

  font-size: 42px;
  color: #22c55e;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.7));
  z-index: 10;
  pointer-events: none;

  /* ADAPTACIÓN PARA MÓVIL Y TABLET */
  @include tablet {
    top: 6px;
    right: 6px;
    font-size: 32px;
  }

  @include mobile {
    top: 4px;
    right: 4px;
    font-size: 24px;
  }
}

/* --- STICKERS DE JOKERS --- */
.sticker-apply-enter-active {
  animation: drop-flat 0.2s ease-out;
}
.sticker-apply-leave-active {
  animation: fade-out 0.1s ease-in;
}

@keyframes drop-flat {
  0% {
    top: -20px;
    opacity: 0;
  }
  100% {
    top: 0;
    opacity: 1;
  }
}

/* Contenedor que reserva el espacio (evita que el grid salte) */
.art-container-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 71 / 95; /* Asegura que el hueco siempre mida lo mismo */
}

/* El contenido animado que "flota" sobre el hueco reservado */
.art-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* Ajuste de animación para que no sea intrusiva */
.reveal-pop-enter-active {
  animation: pop-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes pop-in {
  0% {
    transform: scale(0.9);
    filter: brightness(2) contrast(1.5);
    opacity: 0;
  }
  100% {
    transform: scale(1);
    filter: brightness(1) contrast(1);
    opacity: 1;
  }
}

/* Sticker/Stake apply  */
.sticker-apply-enter-active {
  animation: drop-flat 0.2s ease-out;
}
.sticker-apply-leave-active {
  animation: fade-out 0.1s ease-in;
}

@keyframes drop-flat {
  0% {
    top: -20px;
    opacity: 0;
  }
  100% {
    top: 0;
    opacity: 1;
  }
}

.stake-drop-enter-active {
  animation: drop-bounce 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.stake-drop-leave-active {
  animation: fade-out 0.1s ease-in;
}

@keyframes drop-bounce {
  0% {
    top: -25px;
    opacity: 0;
  }
  60% {
    top: 4px;
    opacity: 1;
  }
  100% {
    top: 0;
    opacity: 1;
  }
}

/* --- ANIMACIÓN EXCLUSIVA PARA CHECK DE CHALLENGE DECKS --- */
.check-pop-enter-active {
  /* Usamos un cubic-bezier elástico para dar el efecto de rebote */
  animation: pop-bounce 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.check-pop-leave-active {
  /* Reusamos la animación de fade-out que ya tienes definida */
  animation: fade-out 0.1s ease-in;
}

@keyframes pop-bounce {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes fade-out {
  0% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}
</style>
