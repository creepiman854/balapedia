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
  <SparkleOverlay />
  <CrtEffects :intensity="settings.crtIntensity" />

  <div id="app-content">
    <AppHeader
      @open-settings="showSettings = true"
      @toggle-credits="showCredits = !showCredits"
      @close-credits="showCredits = false"
    />

    <main class="main-area">
      <router-view />
    </main>
    <AppFooter :is-open="showCredits" @toggle="showCredits = !showCredits" />

    <SettingsModal :is-open="showSettings" @close="showSettings = false" />
    <AuthModal />
  </div>

  <GlobalBlockingOverlay v-if="navigationLocked" />
</template>

<script setup>
import { ref, watch } from "vue";

import { useSettingsStore } from "@/stores/settings";
import { useAuthStore } from "@/stores/auth";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";

import BalatroBackground from "@/components/common/BalatroBackground.vue";
import SparkleOverlay from "@/components/common/SparkleOverlay.vue";
import CrtEffects from "@/components/common/CrtEffects.vue";
import AppHeader from "@/components/common/AppHeader.vue";
import AppFooter from "@/components/common/AppFooter.vue";
import SettingsModal from "@/components/common/SettingsModal.vue";
import AuthModal from "@/components/common/AuthModal.vue";
import GlobalBlockingOverlay from "@/components/common/GlobalBlockingOverlay.vue";

const settings = useSettingsStore();
const authStore = useAuthStore();
const showSettings = ref(false);
const showCredits = ref(false);

const { navigationLocked } = storeToRefs(authStore);
const route = useRoute();

watch(
  () => route.path,
  () => {
    showCredits.value = false;
  },
);
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
