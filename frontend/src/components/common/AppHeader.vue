<!--
  Cabecera global de Balapedia.

  · Logo a la izquierda.
  · Tabs centrales que navegan a /jokers, /consumibles, /collection,
    /achievements. Cada tab tiene su acento (rojo, naranja, etc.).
  · A la derecha: botón cuenta (manda a /login o muestra al usuario)
    + botón ajustes (futuro modal).

  Mantiene el clip-path pixelado y la fuente m6x11plus del diseño.
-->
<template>
  <header class="header">
    <div class="logo">BALA<span>PEDIA</span></div>

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
          @click="navigate"
        >
          {{ tab.label }}
        </button>
      </router-link>
    </nav>

    <button class="login-btn" title="Ajustes" @click="$emit('open-settings')">⚙</button>

    <template v-if="isAuthenticated && user">
      <span class="user-name">{{ user.display_name || user.email || 'Usuario' }}</span>
      <button class="login-btn logged-in" @click="handleLogout">SALIR</button>
    </template>
    <router-link v-else to="/login" custom v-slot="{ navigate }">
      <button class="login-btn" @click="navigate">👤 CUENTA</button>
    </router-link>
  </header>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineEmits(['open-settings'])

const router = useRouter()
const authStore = useAuthStore()
const { isAuthenticated, user } = storeToRefs(authStore)

const tabs = [
  { to: '/jokers',       label: 'JOKERS',      cls: 'nav-jokers',       color: '#2563eb' },
  { to: '/consumibles',  label: 'CONSUMIBLES', cls: 'nav-consumibles',  color: '#d97706' },
  { to: '/achievements', label: 'LOGROS',      cls: 'nav-achievements', color: '#dc2626' },
  { to: '/collection',   label: 'COLECCIÓN',   cls: 'nav-collection',   color: '#059669' },
]

function navBtnStyle(tab, isActive) {
  if (isActive) {
    return {
      boxShadow: `0 4px 16px ${tab.color}60, inset 0 -2px 0 rgba(0,0,0,0.3)`,
    }
  }
  return { filter: 'brightness(0.75) saturate(0.7)' }
}

async function handleLogout() {
  await authStore.logout()
  router.push('/')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

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
}

.logo {
  font-family: 'm6x11plus', monospace;
  font-size: 18px;
  color: #fff;
  letter-spacing: 2px;
  text-shadow:
    0 0 20px rgba(112, 131, 135, 0.9),
    2px 2px 0 rgba(0, 0, 0, 0.8);
  margin-right: 8px;
  flex-shrink: 0;

  span {
    color: $text-2;
  }
}

.nav-group {
  display: flex;
  gap: 8px;
  flex: 1;
  justify-content: center;
}

.nav-btn {
  font-family: 'm6x11plus', monospace;
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

  &:hover {
    transform: scale(1.06);
    filter: brightness(1.2);
  }
  &:active {
    transform: scale(0.94);
    filter: brightness(0.85);
  }
  &.active {
    filter: brightness(1.25);
  }
  &.active::after {
    content: '';
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

.nav-jokers       { background: $tab-jokers; }
.nav-consumibles  { background: $tab-consumibles; }
.nav-achievements { background: $tab-achievements; }
.nav-collection   { background: $tab-collection; }

.login-btn {
  font-family: 'm6x11plus', monospace;
  font-size: 15px;
  color: $text-2;
  background: $panel-dark;
  border: 1px solid $panel-mid;
  padding: 8px 12px;
  cursor: pointer;
  letter-spacing: 0.5px;
  transition: all 0.15s;
  flex-shrink: 0;
  @include pixel-clip;

  &:hover {
    background: $panel-mid;
    transform: scale(1.04);
  }
  &.logged-in {
    background: #1a3a1a;
    border-color: #22c55e;
    color: #22c55e;
  }
}

.user-name {
  font-family: 'm6x11plus', monospace;
  font-size: 15px;
  color: #22c55e;
  letter-spacing: 0.3px;
}
</style>
