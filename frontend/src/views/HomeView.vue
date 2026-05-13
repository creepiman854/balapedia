<template>
  <div class="home-view">
    <h1>Balapedia</h1>
    <p>Tu enciclopedia y tracker de progreso para Balatro.</p>

    <div v-if="isAuthenticated" class="status">
      <p>Sesión iniciada.</p>
      <router-link to="/profile">Ver mi perfil</router-link>
    </div>
    <div v-else class="status">
      <router-link to="/login">Iniciar sesión</router-link>
    </div>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)
</script>

<style scoped>
.home-view {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
  text-align: center;
}
.status {
  margin-top: 2rem;
}
</style>
