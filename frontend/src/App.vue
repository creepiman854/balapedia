<!--
  Shell global de la app.

  Pase final de Jokers:
    · BalatroBackground a z:0 (canvas WebGL, fondo de toda la web).
    · CrtEffects ya solo aporta scanlines (capa fixed, pointer:none).
    · #app-content YA NO aplica filter:url() — era el responsable del
      lag/artifacts en Firefox al scrollear sobre contenido filtrado.
      Sin él, hitboxes 1:1 en TODOS los navegadores.
    · SettingsModal vive dentro de #app-content para recibir las
      scanlines del CRT.

  Resultado: nada de SVG filters aplicados a HTML, nada de
  feDisplacementMap, nada de viñetas. Solo capas decorativas fixed con
  pointer-events:none + el shader WebGL como fondo.
-->
<template>
  <BalatroBackground />
  <!--
    SparkleOverlay vive entre el shader (z:0) y el contenido (z:10).
    Lee el preset actual y solo renderiza destellos para
    tarot/planet/spectral (jokers y default lo ignoran).
  -->
  <SparkleOverlay />
  <CrtEffects :intensity="settings.crtIntensity" />

  <div id="app-content">
    <AppHeader @open-settings="showSettings = true" />

    <main class="main-area">
      <router-view />
    </main>

    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import BalatroBackground from '@/components/common/BalatroBackground.vue'
import SparkleOverlay from '@/components/common/SparkleOverlay.vue'
import CrtEffects from '@/components/common/CrtEffects.vue'
import AppHeader from '@/components/common/AppHeader.vue'
import SettingsModal from '@/components/common/SettingsModal.vue'

const settings = useSettingsStore()
const showSettings = ref(false)
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
