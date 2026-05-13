<template>
  <header>
    <nav>
      <router-link to="/">Inicio</router-link>
      <router-link v-if="!isAuthenticated" to="/login">Login</router-link>
      <router-link v-if="isAuthenticated" to="/profile">Perfil</router-link>
      <span v-if="user" class="user-info">{{ user.email || 'Usuario' }}</span>
    </nav>
  </header>
  <main>
    <router-view />
  </main>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const { isAuthenticated, user } = storeToRefs(authStore)
</script>

<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #f5f5f5;
}
header {
  background: #2c3e50;
  color: white;
  padding: 1rem 2rem;
}
nav {
  display: flex;
  gap: 1.5rem;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}
nav a {
  color: white;
  text-decoration: none;
}
nav a.router-link-active {
  text-decoration: underline;
}
.user-info {
  margin-left: auto;
  opacity: 0.8;
  font-size: 0.9rem;
}
</style>
