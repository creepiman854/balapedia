<template>
  <div class="profile-view">
    <h1>Mi perfil</h1>

    <div v-if="loading">Cargando perfil...</div>
    <div v-else-if="!user" class="error">
      No se pudo cargar el perfil. ¿Backend caído?
    </div>
    <table v-else class="profile-table">
      <tr><th>ID interno</th><td>{{ user.id }}</td></tr>
      <tr><th>Firebase UID</th><td><code>{{ user.firebase_uid }}</code></td></tr>
      <tr><th>Email</th><td>{{ user.email || '—' }}</td></tr>
      <tr><th>Display name</th><td>{{ user.display_name || '—' }}</td></tr>
      <tr><th>Steam ID</th><td>{{ user.steam_id || 'No vinculada' }}</td></tr>
      <tr><th>Cuenta creada</th><td>{{ formatDate(user.created_at) }}</td></tr>
      <tr v-if="user.last_steam_sync">
        <th>Última sync Steam</th>
        <td>{{ formatDate(user.last_steam_sync) }}</td>
      </tr>
    </table>

    <button @click="handleLogout">Cerrar sesión</button>
  </div>
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const { user, loading } = storeToRefs(authStore)

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'home' })
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}
</script>

<style scoped>
.profile-view {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
}
.profile-table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}
.profile-table th,
.profile-table td {
  padding: 0.5rem;
  border-bottom: 1px solid #ddd;
  text-align: left;
}
.profile-table th {
  width: 35%;
  color: #666;
  font-weight: normal;
}
button {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
}
.error {
  color: #c00;
}
code {
  font-size: 0.85rem;
  background: #f0f0f0;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}
</style>
