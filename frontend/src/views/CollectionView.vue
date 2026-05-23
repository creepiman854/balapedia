<!--
  Placeholder de Colección. Subtabs Mazos/Sobres/Vales/Mejoras/Ciegos/
  Etiquetas + grid mixto (cards + filas compactas). En balapedia-views.jsx.
-->
<template>
  <div class="placeholder">
    <h2>COLECCIÓN</h2>
    <p>Próximamente: Mazos, Sobres, Vales, Mejoras, Ciegos y Etiquetas.</p>
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
    color: $tab-collection;
    letter-spacing: 2px;
  }
}
</style>
