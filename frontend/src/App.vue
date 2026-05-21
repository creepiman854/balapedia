<!--
  Shell global de la app.

  Estructura:
    · CrtEffects: capas de fondo + filtros SVG (cargados siempre, los
      filtros se activan vía clase .crt-enabled en #app-content).
    · AppHeader: nav + cuenta + ajustes.
    · <main> con <router-view>.

  El filtro CRT se aplica al envoltorio #app-content, no a #app, para que
  el <svg> con los <defs> de los filtros NO sufra el filtro a sí mismo
  (eso causa un bucle visual feo en algunos navegadores).
-->
<template>
  <CrtEffects :enabled="settings.crt" />

  <div id="app-content" :class="{ 'crt-enabled': settings.crt }">
    <AppHeader @open-settings="openSettings" />

    <main class="main-area">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useSettingsStore } from '@/stores/settings'
import CrtEffects from '@/components/common/CrtEffects.vue'
import AppHeader from '@/components/common/AppHeader.vue'

const settings = useSettingsStore()

function openSettings() {
  // TODO: cuando exista el SettingsModal, abrirlo desde aquí.
  // Por ahora alterna el CRT para que el botón sea funcional.
  settings.setCrt(!settings.crt)
}
</script>

<style lang="scss" scoped>
#app-content {
  position: relative;
  z-index: 10;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.main-area {
  flex: 1;
  min-height: 0;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
}
</style>
