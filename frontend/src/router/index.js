import { createRouter, createWebHistory } from "vue-router";
import { watch } from "vue";
import { useAuthStore } from "@/stores/auth";

const routes = [
  { path: "/", name: "home", component: () => import("@/views/HomeView.vue") },
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

  // Ruta protegida sin sesión → al login
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: "login" };
  }
  // Usuario ya autenticado intentando ir a /login → al perfil
  if (to.name === "login" && authStore.isAuthenticated) {
    return { name: "profile" };
  }
});

export default router;
