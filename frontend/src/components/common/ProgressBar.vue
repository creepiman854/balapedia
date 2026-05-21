<!--
  Barra de progreso pixelada. Soporta etiqueta opcional con conteo.
-->
<template>
  <div class="progress">
    <div v-if="label" class="progress__label">
      <span>{{ label }}</span>
      <span :style="{ color }">{{ value }}/{{ max }}</span>
    </div>
    <div class="progress__track">
      <div
        class="progress__fill"
        :style="{
          width: `${pct}%`,
          background: `linear-gradient(90deg, ${color}99, ${color})`,
          boxShadow: `0 0 8px ${color}`,
        }"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, required: true },
  max: { type: Number, required: true },
  color: { type: String, default: '#3b82f6' },
  label: { type: String, default: '' },
})

const pct = computed(() => (props.max > 0 ? Math.round((props.value / props.max) * 100) : 0))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.progress {
  margin-bottom: 8px;

  &__label {
    display: flex;
    justify-content: space-between;
    font-family: 'm6x11plus', monospace;
    font-size: 11px;
    color: $panel-light;
    margin-bottom: 4px;
  }

  &__track {
    background: $panel-darkest;
    height: 10px;
    overflow: hidden;
    @include pixel-clip-sm;
  }

  &__fill {
    height: 100%;
    transition: width 0.8s ease;
  }
}
</style>
