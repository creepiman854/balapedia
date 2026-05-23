<!--
  Barra de progreso pixelada.

  Pase final de jokers: la etiqueta sale del marco oscuro y vive sobre
  el shader Balatro → tipografía más grande, color blanco y sombra
  sólida sin desenfoque para garantizar contraste sobre cualquier
  punto del fondo (rojo, azul, teal oscuro).
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
  margin-bottom: 10px;

  /*
   * Texto sobre el shader: blanco con drop-shadow sólido sin difusión.
   * Tamaño bumpeado (era 11px → 14px) y peso un poco más alto.
   * Equivalente al `box-shadow: 0 5px 0 #000` del feedback aplicado a
   * texto (text-shadow no admite spread, así que ese cuarto parámetro
   * se omite — el efecto visual es el mismo: ofsset Y de 5px sin blur).
   */
  &__label {
    display: flex;
    justify-content: space-between;
    font-family: 'm6x11plus', monospace;
    font-size: 14px;
    color: #ffffff;
    text-shadow: 0 2px 0 #00000070;
    margin-bottom: 6px;
    letter-spacing: 0.4px;
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
