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
    :class="{ 'arch--selected': isSelected }"
    :style="archStyle"
  >
    <template v-if="stack">
      <div class="deck-shadow deck-shadow--back" />
      <div class="deck-shadow deck-shadow--mid" />
    </template>
    <div
      v-tilt="{ max: 12, scale: 1.07, speed: 320 }"
      class="tilt-wrap"
      @click="emit('select', item)"
      @mouseenter="onEnter"
      @mouseleave="emit('leave')"
    >
      <ItemCardArt
        :item="item"
        :is-locked="isLocked"
        :is-selected="isSelected"
        :accent="accent"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getItemAccent } from '@/constants/items'
import ItemCardArt from './ItemCardArt.vue'

const props = defineProps({
  item: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false },
  colIndex: { type: Number, default: 0 },
  colCount: { type: Number, default: 1 },
  /** Renderiza el efecto "pila de cartas" detrás. Para MAZOS. */
  stack: { type: Boolean, default: false },
})

const emit = defineEmits(['select', 'hover', 'leave'])

const accent = computed(() => getItemAccent(props.item))

const archStyle = computed(() => {
  const base = props.isSelected ? 5 : 1
  if (props.colCount < 2) return { zIndex: base }
  const half = (props.colCount - 1) / 2
  const norm = (props.colIndex - half) / half
  const dropY = norm * norm * 16
  const rotZ = norm * 3.5
  return {
    transform: `translateY(${dropY.toFixed(2)}px) rotate(${rotZ.toFixed(2)}deg)`,
    zIndex: base,
  }
})

function onEnter(e) {
  emit('hover', { item: props.item, target: e.currentTarget })
}
</script>

<style lang="scss" scoped>
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
  z-index: 1;
}

/*
 * Stack: dos cartas "ficticias" detrás de la real, con offset +
 * rotación. Cada una tiene aspect-ratio y border-radius idénticos a
 * la carta real, así parece una pila.
 *
 * Posición: absolute con inset:0 + aspect-ratio explícito para que se
 * dimensione al box de la card sin depender del width del .arch (que
 * en grids extremos puede tener width 0 antes del primer paint).
 */
.deck-shadow {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  aspect-ratio: 71 / 95;
  border-radius: 8px;
  background: linear-gradient(160deg, #1a2a2e 0%, #0d1517 100%);
  border: 1px solid rgba(58, 80, 85, 0.7);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.55);
  pointer-events: none;
}

.deck-shadow--back {
  transform: translate(11px, 9px) rotate(-3deg);
  opacity: 0.42;
  z-index: 0;
}

.deck-shadow--mid {
  transform: translate(5px, 5px) rotate(2deg);
  opacity: 0.6;
  z-index: 0;
}
</style>
