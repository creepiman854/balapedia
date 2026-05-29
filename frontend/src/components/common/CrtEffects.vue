<!--
  Efecto CRT — versión minimalista.

  Líneas de escaneo y aberración cromática
-->
<template>
  <div
    v-show="intensity > 0"
    class="crt-overlay"
    :style="{ '--scan-opacity': scanOpacity, '--scan-darkness': scanDarkness }"
    aria-hidden="true"
  />
</template>

<script setup>
import { computed, watchEffect } from "vue";

const props = defineProps({
  intensity: { type: Number, default: 0.5 },
});

// Opacidad general y oscuridad del escaneo
const scanOpacity = computed(() => 0.55 + 0.45 * props.intensity);
const scanDarkness = computed(() => 0.03 + 0.15 * props.intensity);

// Calculamos la aberración cromática dinámica para la UI (Offset y Transparencia)
const caOffset = computed(() => `${props.intensity * 2.5}px`);
const caAlpha = computed(() => props.intensity * 0.75);

// Inyectamos las variables al :root de la app para que afecten globalmente a los elementos
watchEffect(() => {
  document.documentElement.style.setProperty("--ca-offset", caOffset.value);
  document.documentElement.style.setProperty("--ca-alpha", caAlpha.value.toString());
});
</script>

<style lang="scss" scoped>
.crt-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, var(--scan-darkness)) 2px,
    rgba(0, 0, 0, var(--scan-darkness)) 4px
  );
  opacity: var(--scan-opacity);
}
</style>

<style lang="scss">
/* ESTILOS GLOBALES - Aberración Cromática por Hardware (Sin SVG Filter) */

:root {
  --ca-offset: 0px;
  --ca-alpha: 0;
}

/* 1. Textos: Se hereda nativamente a toda la tipografía de la app.
   (Nota: Si un título tiene un text-shadow propio muy fuerte, el navegador
   lo respetará y no lo romperá, sirviendo de fallback seguro). */
body {
  text-shadow:
    var(--ca-offset) 0px 0px rgba(255, 0, 0, var(--ca-alpha)),
    calc(var(--ca-offset) * -1) 0px 0px rgba(0, 255, 255, var(--ca-alpha));
}

/* 2. Contenedores Visuales: drop-shadow aplica a la silueta exterior
   (Cartas, iconos de la UI, stickers y canvas de fondo) */
.art-container,
iconify-icon,
canvas,
.sticker-overlay {
  filter: drop-shadow(var(--ca-offset) 0px 0px rgba(255, 0, 0, var(--ca-alpha)))
    drop-shadow(calc(var(--ca-offset) * -1) 0px 0px rgba(0, 255, 255, var(--ca-alpha)));
  /* Suaviza la transición cuando mueves el slider */
  transition: filter 0.1s ease-out;
}
</style>
