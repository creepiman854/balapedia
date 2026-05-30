<!--
  Cabecera global de Balapedia.

  · Logo a la izquierda.
  · Tabs centrales que navegan a /jokers, /consumables, /collection,
    /achievements. Cada tab tiene su acento (rojo, naranja, etc.).
  · A la derecha: botón cuenta (manda a /login o muestra al usuario)
    + botón ajustes (futuro modal).

  Mantiene el clip-path pixelado y la fuente m6x11plus del diseño.

  En tablet la cabecera se compacta (nav-buttons + label más pequeños).
  En MÓVIL los nav-buttons salen del header — un botón hamburguesa a la
  izquierda abre un drawer lateral con los mismos enlaces a tamaño
  cómodo. El header además se oculta al hacer scroll hacia abajo
  (controlado por useHeaderStore) y reaparece al subir.
-->
<template>
  <header class="header" :class="{ 'header--hidden': headerStore.hidden && !drawerOpen }">
    <!-- Burger button — visible solo en móvil. Abre el drawer lateral. -->
    <button
      class="burger-btn"
      :class="{ 'burger-btn--open': drawerOpen }"
      title="Menu"
      aria-label="Open menu"
      @click="!authStore.navigationLocked && (drawerOpen = !drawerOpen)"
    >
      <iconify-icon icon="pixel:bars-solid" noobserver />
    </button>

    <div class="logo">
      <img src="/images/balapedia_logo.png" alt="Balapedia Logo" draggable="false" />
    </div>

    <nav class="nav-group">
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        custom
        v-slot="{ navigate, isActive }"
      >
        <button
          :class="['nav-btn', tab.cls, { active: isActive }]"
          :style="navBtnStyle(tab, isActive)"
          @click="!authStore.navigationLocked && navigate()"
        >
          {{ tab.label }}
        </button>
      </router-link>
    </nav>

    <div class="settings-wrapper">
      <button
        class="login-btn"
        title="Settings"
        @click="!authStore.navigationLocked && $emit('open-settings')"
      >
        <iconify-icon icon="pixel:cog" noobserver />
      </button>
    </div>

    <template v-if="isAuthenticated && user">
      <div class="account-wrapper logged-in-wrapper">
        <button
          class="login-btn logged-in"
          @click="!authStore.navigationLocked && authStore.openAuthModal()"
          title="Manage my account"
        >
          <iconify-icon icon="pixel:user-solid" noobserver />
          <span class="login-btn__label">
            {{ user.display_name || user.email || "USER" }}
          </span>
        </button>
      </div>
    </template>

    <template v-else>
      <div class="account-wrapper">
        <button class="login-btn" @click="!authStore.navigationLocked && authStore.openAuthModal()">
          <iconify-icon icon="pixel:user" noobserver />
          <span class="login-btn__label">ACCOUNT</span>
        </button>
      </div>
    </template>
  </header>

  <!--
    Drawer lateral con la navegación a tamaño cómodo.
    Solo se renderiza en móvil — se abre con el botón hamburguesa. El
    backdrop cierra al tocar fuera; el enlace activo se desactiva
    automáticamente al cambiar de ruta (watch sobre route.path).
  -->
  <Teleport to="body">
    <Transition name="drawer-fade">
      <div v-if="drawerOpen" class="drawer-backdrop" @click.self="drawerOpen = false">
        <Transition name="drawer-slide" appear>
          <aside v-if="drawerOpen" class="drawer-panel" @click.stop>
            <header class="drawer-head">
              <div class="logo">
                <img src="/images/balapedia_logo.png" alt="Balapedia Logo" draggable="false" />
              </div>
              <button class="drawer-close" aria-label="Close menu" @click="drawerOpen = false">
                <iconify-icon icon="pixel:window-close-solid" noobserver />
              </button>
            </header>

            <nav class="drawer-nav">
              <router-link
                v-for="tab in tabs"
                :key="`d-${tab.to}`"
                :to="tab.to"
                custom
                v-slot="{ navigate, isActive }"
              >
                <button
                  :class="['drawer-nav-btn', tab.cls, { active: isActive }]"
                  :style="navBtnStyle(tab, isActive)"
                  @click="onDrawerNav(navigate)"
                >
                  {{ tab.label }}
                </button>
              </router-link>
            </nav>
          </aside>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useHeaderStore } from "@/stores/header";

defineEmits(["open-settings"]);

const authStore = useAuthStore();
const { isAuthenticated, user } = storeToRefs(authStore);
const headerStore = useHeaderStore();
const route = useRoute();

const drawerOpen = ref(false);

// Cualquier cambio de ruta cierra el drawer — el usuario espera que
// al tocar un tab navegue y desaparezca el panel sin pasos extra.
watch(
  () => route.path,
  () => {
    drawerOpen.value = false;
  },
);

function onDrawerNav(navigate) {
  if (authStore.navigationLocked) return;
  navigate();
  // El watch sobre route.path también cerraría el drawer, pero esto
  // hace que el cierre se sienta inmediato (no un tick después).
  drawerOpen.value = false;
}

const tabs = [
  { to: "/jokers", label: "JOKERS", cls: "nav-jokers", color: "#2563eb" },
  { to: "/consumables", label: "CONSUMABLES", cls: "nav-consumables", color: "#d97706" },
  { to: "/achievements", label: "ACHIEVEMENTS", cls: "nav-achievements", color: "#dc2626" },
  { to: "/collection", label: "COLLECTION", cls: "nav-collection", color: "#059669" },
];

function navBtnStyle(tab, isActive) {
  if (isActive) {
    return {
      boxShadow: `0 4px 16px ${tab.color}60, inset 0 -2px 0 rgba(0,0,0,0.3)`,
    };
  }
  return { filter: "brightness(0.75) saturate(0.7)" };
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.header {
  background: linear-gradient(180deg, $panel-dark 0%, $shadow 100%);
  border-bottom: 2px solid $panel-mid;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  position: relative;
  z-index: 100;
  box-shadow:
    0 4px 24px rgba(30, 46, 50, 0.95),
    0 2px 8px rgba(0, 0, 0, 0.6);

  // Transición suave para el hide-on-scroll del móvil.
  transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}

// Burger button — invisible por defecto (desktop/tablet).
.burger-btn {
  display: none;
  background: $panel-dark;
  border: none;
  color: $text-1;
  cursor: pointer;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  padding: 0;
  transition:
    background 0.15s,
    transform 0.1s;
  @include pixel-clip;

  iconify-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  @include can-hover {
    &:hover {
      background: $panel-mid;
    }
  }

  &:active {
    transform: scale(0.96);
  }
}

.logo {
  display: flex;
  align-items: center;
  margin-right: 8px;
  flex-shrink: 0;

  img {
    height: 30px;
    width: auto;
    object-fit: contain;
    image-rendering: pixelated; /* Mantiene la estética pixel-art nítida */
    filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.6));
  }
}

.nav-group {
  display: flex;
  gap: 8px;
  flex: 1;
  justify-content: center;
}

.nav-btn {
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  color: #fff;
  border: none;
  padding: 10px 18px;
  cursor: pointer;
  letter-spacing: 1px;
  text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.6);
  transition:
    transform 0.1s,
    filter 0.1s;
  position: relative;
  white-space: nowrap;
  @include pixel-clip;

  @include can-hover {
    &:hover {
      transform: scale(1.06);
      filter: brightness(1.2);
    }
  }
  &:active {
    transform: scale(0.94);
    filter: brightness(0.85);
  }
  &.active {
    filter: brightness(1.25);
  }
  &.active::after {
    content: "";
    position: absolute;
    bottom: -14px;
    left: 50%;
    transform: translateX(-50%);
    width: 6px;
    height: 6px;
    background: currentColor;
    clip-path: polygon(50% 100%, 0 0, 100% 0);
  }
}

.nav-jokers {
  background: $tab-jokers;
}
.nav-consumables {
  background: $tab-consumables;
}
.nav-achievements {
  background: $tab-achievements;
}
.nav-collection {
  background: $tab-collection;
}

/* ── CONTENEDOR DE AJUSTES ── */
.settings-wrapper {
  display: flex;
  @include pixel-stroke($panel-mid);
  transition: filter 0.15s;

  /* Sobreescribimos las propiedades del botón SOLO cuando está dentro de settings */
  .login-btn {
    padding: 8px;
    width: 36px;
  }
}

/* ── CONTENEDOR DE CUENTA ── */
.account-wrapper {
  display: flex;
  @include pixel-stroke($panel-mid);
  transition: filter 0.15s;

  &.logged-in-wrapper {
    @include pixel-stroke(#22c55e);
  }

  /* Sobreescribimos las propiedades del botón SOLO cuando está dentro de cuenta */
  .login-btn {
    padding: 8px 16px;
  }
}

/* ── ESTILOS BASE DEL BOTÓN (Compartidos) ── */
.login-btn {
  font-family: "m6x11plus", monospace;
  font-size: 15px;
  color: $text-2;
  background: $panel-dark;
  border: none;
  cursor: pointer;
  letter-spacing: 0.5px;
  transition: all 0.15s;
  flex-shrink: 0;

  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;

  height: 36px;
  box-sizing: border-box;

  iconify-icon {
    width: 18px;
    height: 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  @include pixel-clip;

  @include can-hover {
    &:hover {
      background: $panel-mid;
      transform: scale(1.04);
    }
  }

  &.logged-in {
    background: #1a3a1a;
    color: #22c55e;
  }
}

.login-btn__label {
  // Truncar nombres largos del display_name para que no rompan el header.
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ──────────────────────────────────────────────────────────────
 * DRAWER LATERAL — solo se ve en móvil, controlado por v-if y por
 * la regla en @include mobile que activa el burger.
 * ────────────────────────────────────────────────────────────── */
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 18, 0.65);
  z-index: 9500;
  display: flex;
  align-items: stretch;
}

.drawer-panel {
  background: $panel-dark;
  width: 78vw;
  max-width: 320px;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.6);
}

.drawer-head {
  background: $panel-mid;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 2px solid $panel-medlight;

  .logo {
    margin: 0;

    img {
      height: 38px;
    }
  }
}

.drawer-close {
  background: transparent;
  border: none;
  color: $text-2;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  line-height: 0;

  iconify-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  @include can-hover {
    &:hover {
      color: $text-1;
    }
  }
}

.drawer-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  overflow-y: auto;
}

.drawer-nav-btn {
  font-family: "m6x11plus", monospace;
  font-size: 18px;
  color: #fff;
  border: none;
  padding: 18px 22px;
  cursor: pointer;
  letter-spacing: 1.5px;
  text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.6);
  text-align: left;
  transition:
    transform 0.1s,
    filter 0.1s;
  white-space: nowrap;
  @include pixel-clip;

  &:active {
    transform: scale(0.97);
    filter: brightness(0.85);
  }

  &.active {
    filter: brightness(1.25);
  }
}

/* Transición del backdrop (fade) */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.18s ease;
}
.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

/* Transición del panel (slide desde la izquierda) */
.drawer-slide-enter-active,
.drawer-slide-leave-active {
  transition: transform 0.26s cubic-bezier(0.32, 0.72, 0, 1);
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  transform: translateX(-100%);
}

/* ──────────────────────────────────────────────────────────────
 * TABLET — header compacto. Reducimos padding, fuente y gap; el
 * label del nombre largo del usuario se acorta a 100px máx.
 * ────────────────────────────────────────────────────────────── */
@include tablet {
  .header {
    padding: 8px 12px;
    gap: 8px;
  }

  .logo {
    margin-right: 4px;

    img {
      height: 24px;
    }
  }

  .nav-group {
    gap: 6px;
    // Si los nav-btn no caben los hacemos scrollables horizontalmente
    // en lugar de envolverlos a una segunda fila (lo cual rompería el
    // diseño visual de la cabecera).
    overflow-x: auto;
    overflow-y: hidden;
    justify-content: flex-start;
    scrollbar-width: none;
    -webkit-overflow-scrolling: touch;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  .nav-btn {
    font-size: 12px;
    padding: 8px 12px;
    letter-spacing: 0.6px;

    &.active::after {
      bottom: -10px;
    }
  }

  .login-btn {
    font-size: 13px;
    height: 34px;
  }

  .account-wrapper .login-btn {
    padding: 6px 12px;
  }
  .settings-wrapper .login-btn {
    padding: 6px;
    width: 32px;
  }

  .login-btn__label {
    max-width: 100px;
  }
}

/* ──────────────────────────────────────────────────────────────
 * MOBILE — el header pasa a "burger + logo grande + iconos".
 * Los nav-btn salen del header y viven dentro del drawer lateral.
 * El header se oculta al hacer scroll hacia abajo (header--hidden
 * se activa desde useHeaderStore via composable en cada vista).
 * ────────────────────────────────────────────────────────────── */
@include mobile {
  .header {
    padding: 12px 12px;
    gap: 10px;

    // Como el JS ya tiene el BOTTOM_GUARD de 120px, podemos volver a animar
    // el margin-bottom de forma segura sin causar rebotes de scroll.
    will-change: transform, margin-bottom;
    transition:
      transform 0.28s cubic-bezier(0.32, 0.72, 0, 1),
      margin-bottom 0.28s cubic-bezier(0.32, 0.72, 0, 1);
  }

  // Estado oculto: transform lo mueve visualmente, margin-bottom elimina su espacio
  .header--hidden {
    transform: translateY(-100%);
    // Altura exacta del header en móvil: 12px padding + 44px botón + 12px padding + 2px border = 70px
    margin-bottom: -70px;
  }

  // Burger visible en móvil.
  .burger-btn {
    display: inline-flex;
  }

  // Nav inline desaparece — la navegación va a través del drawer.
  .nav-group {
    display: none;
  }

  // Logo alineado a la izquierda ahora que tiene espacio al quitar los nav-btns
  .logo {
    margin-right: 0;
    flex: 1;
    display: flex;
    justify-content: flex-start;

    img {
      height: 34px;
    }
  }

  // Account y settings se mantienen como iconos compactos a la derecha.
  .login-btn__label {
    display: none;
  }

  .account-wrapper .login-btn {
    padding: 6px;
    width: 36px;
  }

  .settings-wrapper .login-btn {
    width: 36px;
    padding: 6px;
  }

  .login-btn iconify-icon {
    width: 18px;
    height: 18px;
  }
}
</style>
