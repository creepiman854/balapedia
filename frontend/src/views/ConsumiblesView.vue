<!--
  Placeholder de Consumibles. Iremos portándolo cuando demos por buena
  la vista de jokers. La estructura final (subtabs Tarot/Planeta/Espectral
  + grid + panel de detalle) ya está en balapedia-views-19f9d291.jsx.
-->
<template>
  <div class="placeholder">
    <h2>CONSUMIBLES</h2>
    <p>Próximamente: Tarot, Planeta y Espectral.</p>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
.placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: $text-2;
  font-family: 'm6x11plus', monospace;

  h2 {
    color: $tab-consumibles;
    letter-spacing: 2px;
  }
}
</style>
