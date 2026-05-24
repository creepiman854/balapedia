<!--
  Wrapper interactivo de una carta de item en el grid.

  Sustituye a JokerCard. Genérico: derive el accent de rareza
  (jokers) o de type (consumibles) con `getItemAccent`. Sin
  hipótesis sobre el shape concreto.

  Doble wrapper:
    .arch       → posición base + z-index (arco + selected)
    .tilt-wrap  → tilt+zoom on hover (v-tilt)

  Shadow:
    Ya NO se aplica aquí. La aplica ItemCardArt sobre la <img>
    directamente, así respeta el alpha del png (jokers con
    siluetas no rectangulares no tienen halo de bounding box).
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
}
</style>
