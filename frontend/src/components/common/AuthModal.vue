<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="isOpen" class="modal-backdrop" @click.self="close">
        <div class="modal-panel">
          <button
            v-if="!isCriticalTask"
            class="close-btn"
            @click="close"
            :disabled="busy || isCriticalTask"
          >
            <iconify-icon icon="pixel:window-close-solid" noobserver />
          </button>

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
                <button
                  type="submit"
                  class="balatro-btn primary"
                  :disabled="loading || busy || deletingAccount"
                >
                  {{ loading ? "CARGANDO..." : isSignup ? "REGISTRARME" : "ENTRAR" }}
                </button>
              </form>

              <div class="divider"><span>o</span></div>

              <button
                class="balatro-btn google-btn"
                @click="handleGoogleLogin"
                :disabled="loading || busy || deletingAccount"
              >
                CONTINUAR CON GOOGLE
              </button>

              <button
                class="link-btn"
                type="button"
                @click="isSignup = !isSignup"
                :disabled="busy || deletingAccount"
              >
                {{ isSignup ? "¿Ya tienes cuenta? Inicia sesión" : "¿No tienes cuenta? Crea una" }}
              </button>
            </div>
          </div>

          <div v-else>
            <header class="modal-header">
              <h2 class="modal-title">MI PERFIL</h2>
            </header>

            <div class="modal-body">
              <div v-if="steamLinkMessage || syncMessage" class="notice-wrapper">
                <div v-if="steamLinkMessage" :class="['notice-frame', steamLinkClass]">
                  <div class="notice">
                    {{ steamLinkMessage }}
                  </div>
                </div>

                <div v-if="syncMessage" :class="['notice-frame', syncClass]">
                  <div class="notice">
                    {{ syncMessage }}
                  </div>
                </div>
              </div>

              <div class="profile-info">
                <div class="info-row">
                  <span class="label">Email:</span>
                  <span class="value">{{ user?.email || "—" }}</span>
                </div>
                <div class="info-row">
                  <span class="label">Nombre:</span>
                  <span class="value">
                    {{ user?.display_name || user?.email || "—" }}
                  </span>
                </div>
                <div class="info-row">
                  <span class="label">Steam ID:</span>
                  <span class="value" :class="{ 'steam-linked': user?.steam_id }">
                    {{ user?.steam_id || "No vinculada" }}
                  </span>
                </div>
              </div>

              <div class="actions">
                <div
                  v-if="!user?.steam_id"
                  class="btn-wrapper steam-wrapper"
                  @mouseenter="showTooltip = true"
                  @mouseleave="showTooltip = false"
                  ref="steamWrapperElement"
                >
                  <button
                    class="balatro-btn steam-btn"
                    @click="handleLinkSteam"
                    :disabled="busy || deletingAccount"
                  >
                    <iconify-icon icon="pixel:steam" noobserver /> VINCULAR STEAM
                  </button>
                </div>

                <template v-else>
                  <div class="btn-wrapper sync-wrapper">
                    <button
                      class="balatro-btn sync-btn"
                      @click="handleSyncSteam"
                      :disabled="busy || deletingAccount"
                    >
                      <iconify-icon icon="pixel:refresh-double" noobserver />
                      {{ busy ? "SINCRONIZANDO..." : "SINCRONIZAR CON STEAM" }}
                    </button>
                  </div>
                  <button
                    class="balatro-btn secondary"
                    @click="handleUnlinkSteam"
                    :disabled="busy || deletingAccount"
                  >
                    DESVINCULAR STEAM
                  </button>
                </template>

                <button
                  class="balatro-btn danger"
                  @click="handleLogout"
                  :disabled="busy || deletingAccount"
                >
                  CERRAR SESIÓN
                </button>
                <div class="danger-zone">
                  <button
                    class="balatro-btn delete-account-btn"
                    @click="handleDeleteAccount"
                    :disabled="busy || deletingAccount"
                  >
                    ELIMINAR CUENTA
                  </button>
                </div>
              </div>
            </div>
          </div>

          <p v-if="error" class="error-msg">{{ error }}</p>
        </div>
      </div>
    </Transition>

    <Transition name="modal-fade">
      <div v-if="showTooltip" class="steam-tooltip" ref="tooltipElement">
        Al vincular tu Steam, los logros que tengas desbloqueados allí se sincronizarán
        automáticamente y desbloquearán los Jokers, Vales y Mazos correspondientes en sus
        respectivas vistas.
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router";
import { syncSteamAchievements, describeSyncError } from "@/services/steam_sync";

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
const syncMessage = ref("");
const syncClass = ref("info");
const suppressNextSyncError = ref(false);

// Estado para el tooltip
const showTooltip = ref(false);
const tooltipElement = ref(null);
const steamWrapperElement = ref(null);

const deletingAccount = ref(false);
const syncingSteam = ref(false);
const isCriticalTask = computed(() => deletingAccount.value || syncingSteam.value);

onBeforeRouteLeave(() => {
  if (isCriticalTask.value) {
    return false;
  }
});

function updateTooltipPosition() {
  if (!showTooltip.value || !tooltipElement.value || !steamWrapperElement.value) return;

  const rect = steamWrapperElement.value.getBoundingClientRect();
  const tooltip = tooltipElement.value;

  // Calcular posición (derecha, centrado vertical) con offset de scroll
  const top = rect.top + window.scrollY + rect.height / 2;
  const left = rect.right + window.scrollX + 14;

  // Aplicar estilos directamente
  tooltip.style.top = `${top}px`;
  tooltip.style.left = `${left}px`;
  tooltip.style.transform = `translateY(-50%)`;
}

watch(showTooltip, (isOpen) => {
  if (isOpen) {
    // nextTick es crucial para que el elemento esté en el DOM antes de medir
    nextTick(updateTooltipPosition);
    window.addEventListener("resize", updateTooltipPosition);
    window.addEventListener("scroll", updateTooltipPosition);
  } else {
    // Limpieza
    window.removeEventListener("resize", updateTooltipPosition);
    window.removeEventListener("scroll", updateTooltipPosition);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", preventUnload);

  window.removeEventListener("resize", updateTooltipPosition);
  window.removeEventListener("scroll", updateTooltipPosition);
});

function resetNotices() {
  steamLinkMessage.value = "";
  steamLinkClass.value = "info";

  syncMessage.value = "";
  syncClass.value = "info";
}

// ── Helpers de UI ──
function close() {
  // Durante tareas críticas NO puede cerrarse
  if (isCriticalTask.value) return;

  authStore.closeAuthModal();
  authStore.error = null;

  resetNotices();
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
  resetNotices();

  await authStore.logout();

  close();
}

async function handleDeleteAccount() {
  const confirmation = prompt(
    "¿Seguro que quieres eliminar tu cuenta?\n\n" +
      "Perderás todo el progreso guardado, desbloqueos y sincronizaciones.\n\n" +
      "Escribe ELIMINAR para confirmar.",
  );

  if (confirmation !== "ELIMINAR") {
    return;
  }

  deletingAccount.value = true;
  busy.value = true;

  try {
    await authStore.deleteAccount();

    close();
  } finally {
    busy.value = false;
    deletingAccount.value = false;
  }
}

// ── Lógica de Integración con Steam ──
async function handleLinkSteam() {
  busy.value = true;
  try {
    // Guardamos la ruta actual antes de abandonar la SPA
    sessionStorage.setItem("steam_return_path", route.path);

    await authStore.startSteamLink();
    // No cerramos busy ni el modal porque window.location.href redirige la página completa
  } catch (e) {
    busy.value = false;
  }
}

async function handleUnlinkSteam() {
  if (!confirm("¿Seguro que quieres desvincular tu cuenta de Steam?")) return;

  busy.value = true;

  // Evita mostrar errores de sync provocados por el propio unlink.
  suppressNextSyncError.value = true;

  steamLinkMessage.value = "";
  syncMessage.value = "";

  try {
    await authStore.unlinkSteam();

    steamLinkMessage.value = "Cuenta Steam desvinculada.";
    steamLinkClass.value = "success";

    authStore.notifySteamSync();
  } finally {
    busy.value = false;

    // Se libera en el siguiente tick de microtarea para cubrir
    // cualquier refetch/reactividad inmediata posterior al unlink.
    queueMicrotask(() => {
      suppressNextSyncError.value = false;
    });
  }
}

async function handleSyncSteam({ suppressUnauthorized = false } = {}) {
  if (busy.value) return;

  syncMessage.value = "";
  busy.value = true;
  syncingSteam.value = true;

  try {
    const result = await syncSteamAchievements();
    const s = result.summary;

    const achievementLabel =
      s.newly_unlocked_count === 1 ? "new achievement unlocked" : "new achievements unlocked";

    const itemLabel =
      s.total_items_cascaded === 1
        ? "new item added to your collection"
        : "new items added to your collection";

    syncMessage.value =
      `✓ Steam sync completed.\n` +
      `${s.newly_unlocked_count} ${achievementLabel}\n` +
      `${s.total_items_cascaded} ${itemLabel}.`;

    syncClass.value = "success";

    authStore.notifySteamSync();
  } catch (e) {
    if (suppressNextSyncError.value) {
      return;
    }

    const desc = describeSyncError(e);

    // Ignora el 401 espurio del auto-sync post-vinculación.
    if (suppressUnauthorized && desc.code === "unauthorized") {
      return;
    }

    syncMessage.value = desc.message;
    syncClass.value = "error";
  } finally {
    busy.value = false;
    syncingSteam.value = false;
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
    // Auto-trigger del sync una vez. Si falla, no rompemos el flow de
    // vinculación — el usuario tendrá el botón manual disponible.
    await new Promise((resolve) => setTimeout(resolve, 250));

    handleSyncSteam({
      suppressUnauthorized: true,
    }); // intencional: sin await, corre en background
  }

  // Restauramos la ruta previa
  const returnPath = sessionStorage.getItem("steam_return_path");

  if (returnPath) {
    // Limpiamos la memoria y volvemos a la ruta original (sin los query params de Steam)
    sessionStorage.removeItem("steam_return_path");
    router.replace({ path: returnPath });
  } else {
    // Fallback: si por algún motivo no hay ruta guardada, solo limpiamos la URL
    const currentQuery = { ...route.query };
    delete currentQuery.steam_link;
    router.replace({ query: currentQuery });
  }
}

onMounted(checkSteamRedirect);
watch(() => route.query.steam_link, checkSteamRedirect);
watch(
  () => user.value?.id,
  () => {
    if (!isOpen.value) resetNotices();
  },
);

watch(isAuthenticated, (authenticated) => {
  if (!authenticated && !isOpen.value) {
    resetNotices();
  }
});

watch(isCriticalTask, (active) => {
  if (active) {
    window.addEventListener("beforeunload", preventUnload);
  } else {
    window.removeEventListener("beforeunload", preventUnload);
  }
});

function preventUnload(event) {
  if (!isCriticalTask.value) return;

  event.preventDefault();
  event.returnValue = "";
}
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 18, 0.85);
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
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
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

// El wrapper SOLO maneja layout (column + gap). No aplica pixel-stroke,
// porque eso causaba doble borde cuando el `.notice` interno tenía su
// propia clase semántica (.success/.error/.info) con su propio color.
//
// La regla: una sola fuente de verdad por color de notice. La fuente
// es el `.notice.X`, no el wrapper.
.notice-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  width: 100%;
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
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: #1b2838;
    color: #66c0f4;
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
  margin-bottom: 8px;
}

.danger-zone {
  margin-top: 12px;
  padding-top: 14px;
  border-top: 2px solid rgba(255, 255, 255, 0.08);
}

.delete-account-btn {
  background: #7f1d1d;
  color: #fecaca;

  &:hover:not(:disabled) {
    filter: brightness(1.15);
  }
}

/*
|--------------------------------------------------------------------------
| Notice wrapper
|--------------------------------------------------------------------------
| El borde pixelado vive en el wrapper exterior.
| El contenido interior aplica únicamente el clip pixelado.
| Esto evita artefactos visuales en las esquinas y mantiene
| consistencia con el resto del sistema UI del proyecto.
*/
.notice-frame {
  width: 100%;

  &.success {
    @include pixel-stroke(#22c55e);
  }

  &.error {
    @include pixel-stroke(#dc2626);
  }

  &.info {
    @include pixel-stroke(#3b82f6);
  }
}

/*
|--------------------------------------------------------------------------
| Notice content
|--------------------------------------------------------------------------
*/

.notice {
  width: 100%;
  padding: 12px;
  text-align: center;
  font-family: "m6x11plus", monospace;
  white-space: pre-line;
  @include pixel-clip-sm;

  background: $panel-darkest;

  .notice-frame.success & {
    background: linear-gradient(rgba(34, 197, 94, 0.15), rgba(34, 197, 94, 0.15)), $panel-darkest;
    color: #22c55e;
  }

  .notice-frame.error & {
    background: linear-gradient(rgba(220, 38, 38, 0.15), rgba(220, 38, 38, 0.15)), $panel-darkest;
    color: #ef4444;
  }

  .notice-frame.info & {
    background: linear-gradient(rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.15)), $panel-darkest;
    color: #60a5fa;
  }
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

// Mismo color azul Steam que el link, ligeramente más claro para
// distinguir "vincular" (acción definitiva) de "sincronizar" (acción
// repetible).
.sync-wrapper {
  @include pixel-stroke(#66c0f4);
}

.balatro-btn.sync-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: #2a4d6e;
  color: #9ecde6;
}

.steam-tooltip {
  position: absolute; // Anclado a body, z-index funciona
  width: 260px;
  padding: 10px 12px;
  background: #1b2838; /* Mismo color de fondo que el botón de Steam */
  color: #9ecde6;
  font-family: "m6x11plus", monospace;
  font-size: 12px;
  line-height: 1.45;
  text-align: left;
  white-space: normal;
  letter-spacing: 0.2px;
  z-index: 10000; // Por encima de todo, incluso el modal
  pointer-events: none;
  @include pixel-clip-sm;
}
</style>
