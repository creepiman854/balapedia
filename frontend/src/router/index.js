/**
 * Router de Balapedia.
 *
 * Rutas principales del diseño (Jokers / Consumibles / Logros / Colección)
 * + las vistas existentes (Login, Profile). `/` redirige a `/jokers` que
 * es la vista por defecto cuando no hay sesión.
 *
 * Las guardas esperan a que el listener de Firebase resuelva antes de
 * decidir, para evitar redirecciones incorrectas en el primer render
 * tras un F5 (donde el store inicia con loading=true).
 */
import { createRouter, createWebHistory } from "vue-router";
import { watch } from "vue";
import { useAuthStore } from "@/stores/auth";

const routes = [
  { path: "/", redirect: "/jokers" },

  // Vistas principales (del diseño)
  {
    path: "/jokers",
    name: "jokers",
    component: () => import("@/views/JokersView.vue"),
  },
  {
    path: "/consumibles",
    name: "consumibles",
    component: () => import("@/views/ConsumiblesView.vue"),
  },
  {
    path: "/collection",
    name: "collection",
    component: () => import("@/views/CollectionView.vue"),
  },
  {
    path: "/achievements",
    name: "achievements",
    component: () => import("@/views/AchievementsView.vue"),
  },

  // Vistas heredadas del setup de auth (se mantienen para tests/perfil)
  { path: "/login", name: "login", component: () => import("@/views/LoginView.vue") },
  {
    path: "/profile",
    name: "profile",
    component: () => import("@/views/ProfileView.vue"),
    meta: { requiresAuth: true },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

/**
 * Espera a que el listener inicial de Firebase resuelva (loading=false).
 * Sin esto, las guards se ejecutan antes de saber si hay sesión persistida
 * y toman decisiones equivocadas.
 */
function waitForAuthReady(authStore) {
  if (!authStore.loading) return Promise.resolve();
  return new Promise((resolve) => {
    const stop = watch(
      () => authStore.loading,
      (loading) => {
        if (!loading) {
          stop();
          resolve();
        }
      },
    );
  });
}

router.beforeEach(async (to) => {
  const authStore = useAuthStore();
  await waitForAuthReady(authStore);

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: "login" };
  }
  if (to.name === "login" && authStore.isAuthenticated) {
    return { name: "profile" };
  }
});

export default router;
