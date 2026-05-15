<template>
  <div class="profile-view">
    <h1>Mi perfil</h1>

    <!-- Notificación de resultado del flow Steam -->
    <div v-if="steamLinkMessage" :class="['notice', steamLinkClass]">
      {{ steamLinkMessage }}
    </div>

    <div v-if="isLoadingProfile" class="loading">Cargando perfil...</div>
    <div v-else-if="!user" class="error">No se pudo cargar el perfil. ¿Backend caído?</div>
    <template v-else>
      <table class="profile-table">
        <tr>
          <th>ID interno</th>
          <td>{{ user.id }}</td>
        </tr>
        <tr>
          <th>Firebase UID</th>
          <td>
            <code>{{ user.firebase_uid }}</code>
          </td>
        </tr>
        <tr>
          <th>Email</th>
          <td>{{ user.email || "—" }}</td>
        </tr>
        <tr>
          <th>Display name</th>
          <td>{{ user.display_name || "—" }}</td>
        </tr>
        <tr>
          <th>Steam ID</th>
          <td>
            <span v-if="user.steam_id"
              ><code>{{ user.steam_id }}</code></span
            >
            <span v-else>No vinculada</span>
          </td>
        </tr>
        <tr>
          <th>Cuenta creada</th>
          <td>{{ formatDate(user.created_at) }}</td>
        </tr>
        <tr v-if="user.last_steam_sync">
          <th>Última sync Steam</th>
          <td>{{ formatDate(user.last_steam_sync) }}</td>
        </tr>
      </table>

      <div class="actions">
        <button v-if="!user.steam_id" @click="handleLinkSteam" :disabled="busy">
          Vincular cuenta Steam
        </button>
        <button v-else @click="handleUnlinkSteam" :disabled="busy" class="secondary">
          Desvincular Steam
        </button>
        <button @click="handleLogout" :disabled="busy" class="logout">Cerrar sesión</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { user, loading, isAuthenticated } = storeToRefs(authStore);

const busy = ref(false);
const steamLinkMessage = ref("");
const steamLinkClass = ref("info");

const isLoadingProfile = computed(() => loading.value || (isAuthenticated.value && !user.value));

// Lee el parámetro ?steam_link=... que pone el backend al redirigir,
// muestra notificación, y limpia la URL.
onMounted(async () => {
  const status = route.query.steam_link;
  if (!status) return;

  const STATUS_MAP = {
    success: { msg: "✓ Cuenta Steam vinculada correctamente.", cls: "success" },
    missing_token: { msg: "Falta el token de vinculación.", cls: "error" },
    expired_token: {
      msg: "El token de vinculación ha expirado. Vuelve a intentarlo.",
      cls: "error",
    },
    invalid_token: { msg: "Token de vinculación inválido.", cls: "error" },
    user_not_found: { msg: "Usuario no encontrado.", cls: "error" },
    verification_failed: { msg: "No se pudo verificar la respuesta de Steam.", cls: "error" },
    invalid_claim: { msg: "Steam rechazó la verificación. Vuelve a intentarlo.", cls: "error" },
    invalid_steam_id: { msg: "No se pudo extraer tu Steam ID.", cls: "error" },
    already_linked: { msg: "Esa cuenta Steam ya está vinculada a otro usuario.", cls: "error" },
  };
  const entry = STATUS_MAP[status] || { msg: `Resultado: ${status}`, cls: "info" };
  steamLinkMessage.value = entry.msg;
  steamLinkClass.value = entry.cls;

  // Refresca el perfil tras éxito para que aparezca steam_id
  if (status === "success") {
    await authStore.fetchMe();
  }

  // Limpia el parámetro de la URL sin recargar
  router.replace({ name: "profile" });
});

async function handleLinkSteam() {
  busy.value = true;
  try {
    await authStore.startSteamLink();
    // No retorna: el navegador se redirige a Steam
  } catch (e) {
    busy.value = false;
  }
}

async function handleUnlinkSteam() {
  if (!confirm("¿Seguro que quieres desvincular tu cuenta Steam?")) return;
  busy.value = true;
  try {
    await authStore.unlinkSteam();
    steamLinkMessage.value = "Cuenta Steam desvinculada.";
    steamLinkClass.value = "success";
  } finally {
    busy.value = false;
  }
}

async function handleLogout() {
  await authStore.logout();
  router.push({ name: "home" });
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}
</script>

<style scoped>
.profile-view {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
}
.loading {
  text-align: center;
  color: #666;
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
.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}
button {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.secondary {
  background: #fff;
  border: 1px solid #888;
}
.logout {
  background: #fee;
  border: 1px solid #c66;
}
.notice {
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}
.notice.success {
  background: #efe;
  border: 1px solid #6c6;
  color: #060;
}
.notice.error {
  background: #fee;
  border: 1px solid #c66;
  color: #c00;
}
.notice.info {
  background: #eef;
  border: 1px solid #66c;
  color: #006;
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
