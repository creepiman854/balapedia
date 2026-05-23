<!--
  Placeholder de Logros. Lista vertical con barra de progreso global +
  badges de rareza por logro. En balapedia-views.jsx.
-->
<template>
  <div class="placeholder">
    <h2>LOGROS</h2>
    <p>Próximamente: lista de logros con progreso de Steam.</p>
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
    color: $tab-achievements;
    letter-spacing: 2px;
  }
}
</style>
