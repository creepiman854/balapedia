<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isOpen" class="modal-backdrop" @click.self="close">
        <div class="modal-panel">
          <button class="close-btn" @click="close">✕</button>

          <div v-if="!isAuthenticated">
            <header class="modal-header">
              <h2 class="modal-title">{{ isSignup ? "CREAR CUENTA" : "INICIAR SESIÓN" }}</h2>
            </header>

            <div class="modal-body">
              <form class="auth-form" @submit.prevent="handleEmailSubmit">
                <div class="input-wrapper">
                  <input
                    v-model="email"
                    type="email"
                    placeholder="Email"
                    required
                    autocomplete="email"
                    class="balatro-input"
                  />
                </div>
                <div class="input-wrapper">
                  <input
                    v-model="password"
                    type="password"
                    placeholder="Contraseña"
                    required
                    minlength="6"
                    :autocomplete="isSignup ? 'new-password' : 'current-password'"
                    class="balatro-input"
                  />
                </div>
                <button type="submit" class="balatro-btn primary" :disabled="loading">
                  {{ loading ? "CARGANDO..." : isSignup ? "REGISTRARME" : "ENTRAR" }}
                </button>
              </form>

              <div class="divider"><span>o</span></div>

              <button class="balatro-btn google-btn" @click="handleGoogleLogin" :disabled="loading">
                CONTINUAR CON GOOGLE
              </button>

              <button class="link-btn" type="button" @click="isSignup = !isSignup">
                {{ isSignup ? "¿Ya tienes cuenta? Inicia sesión" : "¿No tienes cuenta? Crea una" }}
              </button>
            </div>
          </div>

          <div v-else>
            <header class="modal-header">
              <h2 class="modal-title">MI PERFIL</h2>
            </header>

            <div class="modal-body">
              <div v-if="steamLinkMessage" :class="['notice', steamLinkClass]">
                {{ steamLinkMessage }}
              </div>

              <div class="profile-info">
                <div class="info-row">
                  <span class="label">Email:</span>
                  <span class="value">{{ user?.email || "—" }}</span>
                </div>
                <div class="info-row">
                  <span class="label">Nombre:</span>
                  <span class="value">{{ user?.display_name || "—" }}</span>
                </div>
                <div class="info-row">
                  <span class="label">Steam ID:</span>
                  <span class="value" :class="{ 'steam-linked': user?.steam_id }">
                    {{ user?.steam_id || "No vinculada" }}
                  </span>
                </div>
              </div>

              <div class="actions">
                <div v-if="!user?.steam_id" class="btn-wrapper steam-wrapper">
                  <button class="balatro-btn steam-btn" @click="handleLinkSteam" :disabled="busy">
                    VINCULAR STEAM
                  </button>
                </div>
                <button
                  v-else
                  class="balatro-btn secondary"
                  @click="handleUnlinkSteam"
                  :disabled="busy"
                >
                  DESVINCULAR STEAM
                </button>
                <button class="balatro-btn danger" @click="handleLogout" :disabled="busy">
                  CERRAR SESIÓN
                </button>
              </div>
            </div>
          </div>

          <p v-if="error" class="error-msg">{{ error }}</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useRoute, useRouter } from "vue-router";

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

const { isAuthenticated, user, error, loading, isAuthModalOpen } = storeToRefs(authStore);

// Enlazamos la visibilidad del modal al store
const isOpen = computed(() => isAuthModalOpen.value);

// Estado local de los formularios
const email = ref("");
const password = ref("");
const isSignup = ref(false);
const busy = ref(false);

// Estado local para los mensajes de Steam (migrado desde ProfileView)
const steamLinkMessage = ref("");
const steamLinkClass = ref("info");

// ── Helpers de UI ──
function close() {
  authStore.closeAuthModal();
  // Limpiamos los estados de error al cerrar para que no persistan en futuras aperturas
  authStore.error = null;
  steamLinkMessage.value = "";
}

// ── Lógica de Login/Signup ──
async function handleEmailSubmit() {
  try {
    if (isSignup.value) await authStore.signupWithEmail(email.value, password.value);
    else await authStore.loginWithEmail(email.value, password.value);
  } catch (e) {
    /* El error técnico ya es capturado y traducido por authStore.error */
  }
}

async function handleGoogleLogin() {
  try {
    await authStore.loginWithGoogle();
  } catch (e) {
    /* El error técnico ya es capturado y traducido por authStore.error */
  }
}

async function handleLogout() {
  await authStore.logout();
  close();
}

// ── Lógica de Integración con Steam ──
async function handleLinkSteam() {
  busy.value = true;
  try {
    await authStore.startSteamLink();
    // No cerramos busy ni el modal porque window.location.href redirige la página completa
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

/**
 * Listener de redirección de Steam.
 * Si el usuario vuelve del flujo de OAuth, la URL traerá un parámetro `steam_link`.
 * Lo interceptamos para mostrar el resultado directamente en el modal de cuenta y
 * limpiamos la URL sin recargar la página.
 */
async function checkSteamRedirect() {
  const status = route.query.steam_link;
  if (!status) return;

  // Forzamos la apertura del modal para mostrar el resultado
  authStore.openAuthModal();

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

  // Si la vinculación fue exitosa, forzamos un re-fetch de /api/me para ver el steam_id
  if (status === "success") {
    await authStore.fetchMe();
  }

  // Limpiamos la URL sin recargar la página (reemplazando la ruta actual sin el query parameter)
  const currentQuery = { ...route.query };
  delete currentQuery.steam_link;
  router.replace({ query: currentQuery });
}

onMounted(checkSteamRedirect);
watch(() => route.query.steam_link, checkSteamRedirect);
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 18, 0.85); // Oscurece el fondo sin tapar el shader por completo
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal-panel {
  background: $panel-dark;
  width: 100%;
  max-width: 420px;
  position: relative;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.8);
  @include pixel-clip;
}

.modal-header {
  background: $panel-mid;
  padding: 24px 32px 20px;
  text-align: center;
  border-bottom: 2px solid rgba(255, 255, 255, 0.05);
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 16px;
  background: transparent;
  border: none;
  color: $text-3;
  font-family: "m6x11plus", monospace;
  font-size: 20px;
  cursor: pointer;
  transition: color 0.15s;

  &:hover {
    color: #e8443a;
  }
}

.modal-title {
  font-family: "m6x11plus", monospace;
  color: #fff;
  font-size: 24px;
  margin: 0;
  text-shadow: 0 3px 0 rgba(0, 0, 0, 0.7);
}

.modal-body {
  padding: 24px 32px 32px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── Wrappers para los bordes pixelados ── */
.input-wrapper {
  display: flex;
  @include pixel-stroke($panel-mid);
  transition: filter 0.15s;

  /* :focus-within aplica el borde azul si el input interno está seleccionado */
  &:focus-within {
    @include pixel-stroke(#2563eb);
  }
}

.btn-wrapper {
  display: flex;
}

.steam-wrapper {
  @include pixel-stroke(#66c0f4);
}

.balatro-input {
  width: 100%;
  background: $panel-darkest;
  border: none;
  color: $text-1;
  font-family: "m6x11plus", monospace;
  font-size: 16px;
  padding: 12px;
  outline: none;
  @include pixel-clip-sm;
}

.balatro-btn {
  font-family: "m6x11plus", monospace;
  font-size: 16px;
  padding: 12px;
  cursor: pointer;
  color: #fff;
  border: none;
  transition:
    transform 0.1s,
    filter 0.1s;
  width: 100%; /* Añadido para que llene el wrapper */
  @include pixel-clip-sm;

  &:hover:not(:disabled) {
    transform: scale(1.02);
    filter: brightness(1.15);
  }

  &:active:not(:disabled) {
    transform: scale(0.98);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &.primary {
    background: #2563eb;
  }
  &.google-btn {
    background: #fff;
    color: #111;
  }

  &.steam-btn {
    background: #1b2838;
    color: #66c0f4;
    /* Eliminamos el pixel-stroke de aquí.
       El hover ahora solo necesita el brightness genérico. */
  }

  &.secondary {
    background: $panel-mid;
    color: $text-2;
  }
  &.danger {
    background: #dc2626;
    margin-top: 16px;
  }
}

.profile-info {
  background: rgba(0, 0, 0, 0.3);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  @include pixel-clip-sm;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-family: "m6x11plus", monospace;
  font-size: 16px;

  .label {
    color: $text-3;
  }
  .value {
    color: $text-1;
  }
  .steam-linked {
    color: #22c55e;
  }
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.divider {
  text-align: center;
  position: relative;
  color: $text-3;
  font-family: "m6x11plus", monospace;

  &::before,
  &::after {
    content: "";
    position: absolute;
    top: 50%;
    width: 40%;
    height: 1px;
    background: $panel-mid;
  }
  &::before {
    left: 0;
  }
  &::after {
    right: 0;
  }
}

.link-btn {
  background: none;
  border: none;
  color: #3b82f6;
  font-family: "m6x11plus", monospace;
  cursor: pointer;
  font-size: 14px;
}

.error-msg {
  text-align: center;
  color: #e8443a;
  font-family: "m6x11plus", monospace;
  margin-top: 8px;
}

.notice {
  padding: 12px;
  text-align: center;
  font-family: "m6x11plus", monospace;
  @include pixel-clip-sm;
}
.notice.success {
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid #22c55e;
  color: #22c55e;
}
.notice.error {
  background: rgba(220, 38, 38, 0.2);
  border: 1px solid #dc2626;
  color: #ef4444;
}
.notice.info {
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid #3b82f6;
  color: #60a5fa;
}

/* Transición del modal */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
