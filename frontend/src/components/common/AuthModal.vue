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

          <div v-if="!isAuthenticated" class="modal-section">
            <header class="modal-header">
              <h2 class="modal-title">{{ isSignup ? "SIGN UP" : "LOG IN" }}</h2>
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
                    placeholder="Password"
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
                  {{ loading ? "LOADING..." : isSignup ? "SIGN UP" : "LOG IN" }}
                </button>
              </form>

              <div class="divider"><span>or</span></div>

              <button
                class="balatro-btn google-btn"
                @click="handleGoogleLogin"
                :disabled="loading || busy || deletingAccount"
              >
                <iconify-icon icon="pixel:google" noobserver />
                CONTINUE WITH GOOGLE
              </button>

              <button
                class="link-btn"
                type="button"
                @click="isSignup = !isSignup"
                :disabled="busy || deletingAccount"
              >
                {{
                  isSignup ? "Already have an account? Log in" : "Don't have an account? Create one"
                }}
              </button>
            </div>
          </div>

          <div v-else class="modal-section">
            <header class="modal-header">
              <h2 class="modal-title">MY PROFILE</h2>
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
                  <span class="label">Name:</span>
                  <span class="value">
                    {{ user?.display_name || user?.email || "—" }}
                  </span>
                </div>
                <div class="info-row">
                  <span class="label">Steam ID:</span>
                  <span class="value" :class="{ 'steam-linked': user?.steam_id }">
                    {{ user?.steam_id || "Not linked" }}
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
                    <iconify-icon icon="pixel:steam" noobserver /> LINK STEAM
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
                      {{ busy ? "SYNCING..." : "SYNC WITH STEAM" }}
                    </button>
                  </div>
                  <button
                    class="balatro-btn secondary"
                    @click="handleUnlinkSteam"
                    :disabled="busy || deletingAccount"
                  >
                    UNLINK STEAM
                  </button>
                </template>

                <button
                  class="balatro-btn danger"
                  @click="handleLogout"
                  :disabled="busy || deletingAccount"
                >
                  LOG OUT
                </button>
                <div class="danger-zone">
                  <button
                    class="balatro-btn delete-account-btn"
                    @click="handleDeleteAccount"
                    :disabled="busy || deletingAccount"
                  >
                    DELETE ACCOUNT
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
        By linking your Steam account, your unlocked achievements will automatically sync, unlocking
        the corresponding Jokers, Vouchers, and Decks in their respective sections.
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
const { lockNavigation, unlockNavigation } = authStore;
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

// Estado local para los mensajes de Steam
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

  const top = rect.top + window.scrollY + rect.height / 2;
  const left = rect.right + window.scrollX + 14;

  tooltip.style.top = `${top}px`;
  tooltip.style.left = `${left}px`;
  tooltip.style.transform = `translateY(-50%)`;
}

watch(showTooltip, (isOpen) => {
  if (isOpen) {
    nextTick(updateTooltipPosition);
    window.addEventListener("resize", updateTooltipPosition);
    window.addEventListener("scroll", updateTooltipPosition);
  } else {
    window.removeEventListener("resize", updateTooltipPosition);
    window.removeEventListener("scroll", updateTooltipPosition);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", preventUnload);
  window.removeEventListener("resize", updateTooltipPosition);
  window.removeEventListener("scroll", updateTooltipPosition);
  window.removeEventListener("keydown", handleEsc);
});

function resetNotices() {
  steamLinkMessage.value = "";
  steamLinkClass.value = "info";
  syncMessage.value = "";
  syncClass.value = "info";
}

// ── Helpers de UI ──
function close() {
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
    "Are you sure you want to delete your account?\n\n" +
      "You will lose all your saved progress, unlocks, and syncs.\n\n" +
      "Type DELETE to confirm.",
  );

  if (confirmation !== "DELETE") {
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
    sessionStorage.setItem("steam_return_path", route.path);
    await authStore.startSteamLink();
  } catch (e) {
    busy.value = false;
  }
}

async function handleUnlinkSteam() {
  if (!confirm("Are you sure you want to unlink your Steam account?")) return;

  busy.value = true;
  suppressNextSyncError.value = true;
  steamLinkMessage.value = "";
  syncMessage.value = "";

  try {
    await authStore.unlinkSteam();
    steamLinkMessage.value = "Steam account unlinked.";
    steamLinkClass.value = "success";
    authStore.notifySteamSync();
  } finally {
    busy.value = false;
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

function handleEsc(event) {
  if (event.key !== "Escape") return;
  if (isCriticalTask.value) return;
  close();
}

// FIX: el archivo original tenía DOS onMounted(checkSteamRedirect)
// — uno como bloque y otro como `onMounted(checkSteamRedirect)`. El
// segundo era residuo de un refactor y disparaba el redirect dos veces.
// Lo dejamos en uno solo aquí.
onMounted(() => {
  checkSteamRedirect();
  window.addEventListener("keydown", handleEsc);
});

async function checkSteamRedirect() {
  const status = route.query.steam_link;
  if (!status) return;

  authStore.openAuthModal();

  const STATUS_MAP = {
    success: { msg: "✓ Steam account linked successfully.", cls: "success" },
    missing_token: { msg: "Linking token is missing.", cls: "error" },
    expired_token: {
      msg: "The linking token has expired. Please try again.",
      cls: "error",
    },
    invalid_token: { msg: "Invalid linking token.", cls: "error" },
    user_not_found: { msg: "User not found.", cls: "error" },
    verification_failed: { msg: "Could not verify Steam response.", cls: "error" },
    invalid_claim: { msg: "Steam verification rejected. Please try again.", cls: "error" },
    invalid_steam_id: { msg: "Could not retrieve your Steam ID.", cls: "error" },
    already_linked: { msg: "That Steam account is already linked to another user.", cls: "error" },
  };

  const entry = STATUS_MAP[status] || { msg: `Resultado: ${status}`, cls: "info" };
  steamLinkMessage.value = entry.msg;
  steamLinkClass.value = entry.cls;

  if (status === "success") {
    await authStore.fetchMe();
    await new Promise((resolve) => setTimeout(resolve, 250));
    handleSyncSteam({ suppressUnauthorized: true });
  }

  const returnPath = sessionStorage.getItem("steam_return_path");

  if (returnPath) {
    sessionStorage.removeItem("steam_return_path");
    router.replace({ path: returnPath });
  } else {
    const currentQuery = { ...route.query };
    delete currentQuery.steam_link;
    router.replace({ query: currentQuery });
  }
}

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
    lockNavigation();
    window.addEventListener("beforeunload", preventUnload);
  } else {
    unlockNavigation();
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
  // z-index explícito: el close-btn vive al MISMO nivel que las secciones
  // de form/profile, por lo que sin z-index quedaba por debajo en mobile.
  z-index: 2;

  @include can-hover {
    &:hover {
      color: #e8443a;
    }
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

  @include can-hover {
    &:hover:not(:disabled) {
      transform: scale(1.02);
      filter: brightness(1.15);
    }
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
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
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
    word-break: break-all;
    text-align: right;
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

  @include can-hover {
    &:hover:not(:disabled) {
      filter: brightness(1.15);
    }
  }
}

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

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

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
  position: absolute;
  width: 260px;
  padding: 10px 12px;
  background: #1b2838;
  color: #9ecde6;
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  line-height: 1.45;
  text-align: left;
  white-space: normal;
  letter-spacing: 0.2px;
  z-index: 10000;
  pointer-events: none;
  @include pixel-clip-sm;
}

/* ──────────────────────────────────────────────────────────────
 * TABLET — el modal aumenta un poco para aprovechar el ancho.
 * El tooltip flotante de "LINK STEAM" se oculta porque no hay
 * hover en dispositivos táctiles.
 * ────────────────────────────────────────────────────────────── */
@include tablet-only {
  .modal-panel {
    max-width: 520px;
  }
}

@include tablet {
  // Cubre tablet + mobile: ocultar el tooltip flotante en touch.
  .steam-tooltip {
    display: none;
  }
}

/* ──────────────────────────────────────────────────────────────
 * MOBILE/TABLET — full-screen sheet con SCROLL DEL PROPIO BACKDROP.
 *
 * Cambios respecto al pase anterior (que rompía la interacción):
 *
 *   · Antes el modal-panel era flex column con `> div { flex:1 }` y el
 *     modal-body absorbía el scroll. En iOS Safari esto producía una
 *     mezcla de stacking + overflow + filter (pixel-stroke usa
 *     drop-shadow filter, que crea su propio compositor) que dejaba
 *     los inputs y botones sin recibir eventos de tap. Resultado:
 *     "nada funciona en móvil".
 *
 *   · La solución es más sencilla: hacemos que el backdrop sea el
 *     contenedor scrollable y dejamos al modal-panel altura natural
 *     (min-height: 100% para llenar la pantalla aunque el contenido
 *     sea corto). Sin flex column anidado, sin overflow:auto sobre
 *     elementos con filter. Pointer events fluyen normales.
 *
 *   · El close-btn además sube a z-index: 2 para que no se quede por
 *     debajo de la sección visible.
 * ────────────────────────────────────────────────────────────── */
@include tablet {
  .modal-backdrop {
    // backdrop pasa a ser el scroll container.
    align-items: stretch;
    justify-content: stretch;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
    backdrop-filter: none;
    background: $panel-dark;
    padding: 0;
  }

  .modal-panel {
    width: 100%;
    max-width: 100%;
    min-height: 100%;
    height: auto;
    box-shadow: none;
    clip-path: none;
    padding-bottom: 24px;
    // Nada de flex column tricks — el panel es flujo normal de bloque.
    display: block;
  }

  .modal-section {
    // Sin flex magic; solo bloque normal.
    display: block;
  }

  .modal-header {
    padding: 22px 24px 18px;
  }

  .modal-title {
    font-size: 22px;
  }

  .modal-body {
    padding: 22px 24px 28px;
    gap: 14px;
  }

  .close-btn {
    top: 14px;
    right: 16px;
    font-size: 22px;
  }
}

@include mobile {
  .modal-backdrop {
    background: $panel-dark;
  }

  .modal-header {
    padding: 18px 18px 14px;
  }

  .modal-title {
    font-size: 20px;
  }

  .modal-body {
    padding: 18px 18px 24px;
  }

  .balatro-input,
  .balatro-btn {
    font-size: 15px;
    padding: 14px 12px; // tap targets cómodos
  }

  .info-row {
    font-size: 14px;
    gap: 10px;
  }

  .link-btn {
    font-size: 13px;
    padding-top: 8px;
  }

  .error-msg {
    font-size: 14px;
    padding: 0 18px 12px;
  }
}
</style>
