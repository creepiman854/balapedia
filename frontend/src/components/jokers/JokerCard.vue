<!--
  Wrapper interactivo de una carta de joker en el grid.
  · Aplica el drop-shadow y escala cuando está seleccionada.
  · Emite eventos `select`, `hover` (con bounding rect) y `leave`.

  Cambio importante respecto al diseño original: el click ya NO marca como
  desbloqueado — la unlock-state es server-side, viene del backend a
  través de `joker.unlocked_for_me` y se modifica únicamente vía sync de
  Steam. El click aquí solo selecciona para enseñar el panel de detalle.
-->
<template>
  <div
    class="joker-card-wrap"
    :style="wrapStyle"
    @click="$emit('select', joker)"
    @mouseenter="onMouseEnter"
    @mouseleave="$emit('leave')"
  >
    <JokerCardArt :joker="joker" :is-locked="isLocked" :show-label="false" />
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
})

const emit = defineEmits(['select', 'hover', 'leave'])

const r = computed(() => getRarity(props.joker.rarity))

const wrapStyle = computed(() => ({
  cursor: 'pointer',
  transition: 'transform 0.15s ease, filter 0.15s ease',
  filter: props.isSelected
    ? `drop-shadow(0 0 12px ${r.value.color}) drop-shadow(0 4px 10px rgba(0,0,0,0.9))`
    : 'drop-shadow(0 4px 8px rgba(0,0,0,0.6))',
  transform: props.isSelected ? 'scale(1.06)' : 'scale(1)',
}))

function onMouseEnter(e) {
  emit('hover', { joker: props.joker, target: e.currentTarget })
}
</script>

<style lang="scss" scoped>
.joker-card-wrap:hover {
  transform: scale(1.06) !important;
}
</style>
