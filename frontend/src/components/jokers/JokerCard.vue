<!--
  Wrapper interactivo de una carta de joker en el grid.

  Doble wrapper: .arch (posición base por columna) + .tilt-wrap (tilt+zoom
  en hover). Esto evita que ambos transforms se pisen mutuamente.

  Pase 5: z-index sobre los vecinos cuando hay HOVER, no solo cuando
  está seleccionada. Antes el zoom de hover quedaba "por debajo" de las
  cartas adyacentes; ahora la carta hovereada queda claramente encima.
-->
<template>
  <div
    class="arch"
    :class="{ 'arch--selected': isSelected }"
    :style="archStyle"
  >
    <div
      v-tilt="{ max: 12, scale: 1.07, speed: 320 }"
      class="tilt-wrap"
      :style="tiltStyle"
      @click="emit('select', joker)"
      @mouseenter="onEnter"
      @mouseleave="emit('leave')"
    >
      <JokerCardArt :joker="joker" :is-locked="isLocked" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getRarity } from '@/constants/rarity'
import JokerCardArt from './JokerCardArt.vue'

const props = defineProps({
  joker: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false },
  colIndex: { type: Number, default: 0 },
  colCount: { type: Number, default: 1 },
})

const emit = defineEmits(['select', 'hover', 'leave'])

const r = computed(() => getRarity(props.joker.rarity))

/**
 * Arco por fila — solo translateY + rotateZ. El z-index BASE lo damos
 * aquí; el efecto hover lo sobreescribe en CSS para no depender de
 * mousemove state en JS.
 */
const archStyle = computed(() => {
  const base = props.isSelected ? 5 : 1
  if (props.colCount < 2) {
    return { zIndex: base }
  }
  const half = (props.colCount - 1) / 2
  const norm = (props.colIndex - half) / half
  const dropY = norm * norm * 16
  const rotZ = norm * 3.5
  return {
    transform: `translateY(${dropY.toFixed(2)}px) rotate(${rotZ.toFixed(2)}deg)`,
    zIndex: base,
  }
})

/*
 * Firefox perf: box-shadow en vez de filter:drop-shadow.
 *   drop-shadow crea un buffer offscreen por cada card (150 buffers →
 *   GPU saturada en Firefox). box-shadow lo pinta directo sobre la
 *   capa del padre. Visualmente equivalente porque la card es
 *   rectangular con border-radius (el shadow respeta el radio).
 */
const tiltStyle = computed(() => ({
  cursor: 'pointer',
  boxShadow: props.isSelected
    ? `0 0 14px ${r.value.color}, 0 6px 14px rgba(0,0,0,0.9)`
    : '0 4px 8px rgba(0,0,0,0.55)',
  borderRadius: '8px', // coincide con el border-radius interno de las cards
}))

function onEnter(e) {
  emit('hover', { joker: props.joker, target: e.currentTarget })
}
</script>

<style lang="scss" scoped>
.arch {
  width: 100%;
  display: block;
  position: relative;
  transition: transform 0.25s ease, z-index 0s linear 0s;

  /*
   * En hover subimos por encima del :selected (que está en z-index 5),
   * para que la carta hovereada quede sobre la seleccionada también.
   * Se aplica en CSS y no en JS para no acoplar al evento mousemove.
   */
  &:hover {
    z-index: 10 !important;
  }
}

.arch--selected {
  /* Mismo z-index base. El hover sigue ganando. */
  z-index: 5;
}

.tilt-wrap {
  width: 100%;
  display: block;
}
</style>
