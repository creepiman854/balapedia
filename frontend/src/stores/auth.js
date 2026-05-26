/**
 * Store Pinia de autenticación.
 *
 * Mantiene dos estados paralelos:
 * - `firebaseUser`: el objeto de Firebase Auth (cliente).
 * - `user`: el objeto que devuelve nuestra API /api/me (BD de Balapedia,
 * con id interno, steam_id si vinculado, etc.).
 *
 * El listener `onAuthStateChanged` sincroniza ambos: cada vez que cambia
 * el estado en Firebase (login, logout, refresco de página), se actualiza
 * `firebaseUser` y se hace fetch de `/api/me` si hay sesión activa.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
} from "firebase/auth";
import { firebaseAuth } from "@/services/firebase";
import { api } from "@/services/api";

export const useAuthStore = defineStore("auth", () => {
  const firebaseUser = ref(null);
  const user = ref(null);
  const loading = ref(true);
  const error = ref(null);

  // Estado del Modal Unificado (Login / Profile)
  const isAuthModalOpen = ref(false);

  const isAuthenticated = computed(() => !!firebaseUser.value);

  // Tras un sync con Steam, las views (Jokers/Colección/Logros) se
  // re-fetchean para mostrar los nuevos unlocks. Esto se coordina con
  // un ref que las views observan via watch().
  //
  // Por qué un ref aquí y no un eventBus: ya tenemos el authStore como
  // fuente de verdad de "estado del usuario actual". Un sync IS un evento
  // de usuario, así que cabe natural. Cero dependencias nuevas.
  const lastSyncedAt = ref(null);

  function notifySteamSync() {
    lastSyncedAt.value = new Date();
  }

  // ── Helpers UI ──
  function openAuthModal() {
    isAuthModalOpen.value = true;
  }

  function closeAuthModal() {
    isAuthModalOpen.value = false;
  }

  /** Llamar una sola vez al arrancar la app (desde main.js). */
  function init() {
    onAuthStateChanged(firebaseAuth, async (fbUser) => {
      firebaseUser.value = fbUser;
      if (fbUser) {
        await fetchMe();
      } else {
        user.value = null;
      }
      loading.value = false;
    });
  }

  async function fetchMe() {
    try {
      const response = await api.get("/api/me");
      user.value = response.data;
    } catch (e) {
      console.error("Error fetching /api/me:", e);
      user.value = null;
    }
  }

  async function loginWithEmail(email, password) {
    error.value = null;
    try {
      await signInWithEmailAndPassword(firebaseAuth, email, password);
    } catch (e) {
      error.value = _translateFirebaseError(e);
      throw e;
    }
  }

  async function signupWithEmail(email, password) {
    error.value = null;
    try {
      await createUserWithEmailAndPassword(firebaseAuth, email, password);
    } catch (e) {
      error.value = _translateFirebaseError(e);
      throw e;
    }
  }

  async function loginWithGoogle() {
    error.value = null;
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(firebaseAuth, provider);
    } catch (e) {
      error.value = _translateFirebaseError(e);
      throw e;
    }
  }

  async function deleteAccount() {
    error.value = null;

    try {
      await api.delete("/api/delete-account");

      // Logout Firebase después de borrar el user interno
      await signOut(firebaseAuth);

      user.value = null;
    } catch (e) {
      error.value = e.response?.data?.error || "No se pudo eliminar la cuenta";

      throw e;
    }
  }

  async function logout() {
    error.value = null;
    await signOut(firebaseAuth);
  }

  async function startSteamLink() {
    error.value = null;
    try {
      const response = await api.get("/api/auth/steam/start");
      // Redirige el navegador a Steam
      window.location.href = response.data.redirect_url;
    } catch (e) {
      error.value = "No se pudo iniciar la vinculación con Steam";
      throw e;
    }
  }

  async function unlinkSteam() {
    error.value = null;
    try {
      await api.post("/api/auth/steam/unlink");
      await fetchMe(); // refresca el perfil para que steam_id desaparezca
    } catch (e) {
      error.value = e.response?.data?.error || "Error desvinculando Steam";
      throw e;
    }
  }

  /** Traduce códigos de error técnicos de Firebase a mensajes legibles. */
  function _translateFirebaseError(e) {
    const code = e.code || "";
    const map = {
      "auth/invalid-email": "Email inválido",
      "auth/user-disabled": "Cuenta deshabilitada",
      "auth/user-not-found": "Usuario no encontrado",
      "auth/wrong-password": "Contraseña incorrecta",
      "auth/invalid-credential": "Credenciales inválidas",
      "auth/email-already-in-use": "El email ya está registrado",
      "auth/weak-password": "La contraseña es demasiado débil (mín. 6 caracteres)",
      "auth/popup-closed-by-user": "Cancelaste el login con Google",
      "auth/network-request-failed": "Error de red. Verifica tu conexión.",
    };
    return map[code] || e.message || "Error desconocido";
  }

  return {
    firebaseUser,
    user,
    loading,
    error,
    isAuthenticated,
    isAuthModalOpen,
    openAuthModal,
    closeAuthModal,
    init,
    fetchMe,
    loginWithEmail,
    signupWithEmail,
    loginWithGoogle,
    logout,
    deleteAccount,
    startSteamLink,
    unlinkSteam,
    lastSyncedAt,
    notifySteamSync,
  };
});
