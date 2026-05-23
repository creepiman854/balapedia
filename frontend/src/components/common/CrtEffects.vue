<!--
  Efecto CRT — versión minimalista.

  Decisiones tomadas en este pase:
   · Fuera el barrel warp (rompía hitboxes y se desplazaba con scroll).
   · Fuera la curvatura simulada con border-radius en las esquinas
     (no encajaba con el estilo Balatro).
   · Fuera la viñeta (.crt-lens) — molestaba más que ayudaba.
   · Fuera la aberración cromática vía filter:url() — causaba lag/
     artifacts en Firefox cuando se aplicaba al contenido scrollable.
   · Fuera la imagen estática de fondo (.bg-layer) y las cartas
     flotantes — ahora el fondo lo aporta BalatroBackground (shader).

  Lo que queda: solo las líneas de escaneo, controladas por el slider
  de intensidad CRT del SettingsModal. Capa fija con pointer-events:
  none → nunca intercepta clicks.
-->
<template>
  <div
    v-show="intensity > 0"
    class="crt-overlay"
    :style="{ opacity: scanOpacity }"
    aria-hidden="true"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  intensity: { type: Number, default: 0.5 },
})

// Opacidad mínima 0.55 cuando el slider está casi en 0 pero no del todo;
// con v-show, la capa desaparece por completo cuando intensity = 0.
const scanOpacity = computed(() => 0.55 + 0.45 * props.intensity)
</script>

<style lang="scss" scoped>
.crt-overlay {
  position: fixed;
  inset: 0;
  /*
   * Por encima del modal de ajustes (z-index 9999) para que, mientras
   * el usuario mueve el slider de intensidad CRT, vea el efecto en
   * tiempo real superponiéndose también sobre el propio modal.
   */
  z-index: 99999;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.03) 2px,
    rgba(0, 0, 0, 0.03) 4px
  );
}
</style>
