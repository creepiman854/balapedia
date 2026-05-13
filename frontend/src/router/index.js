import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomeView.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      path: "/profile",
      name: "profile",
      component: () => import("@/views/ProfileView.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

/** Guard de rutas autenticadas. */
router.beforeEach((to) => {
  const authStore = useAuthStore();
  // Si la ruta requiere auth y el usuario no está autenticado, redirige.
  // Esperamos a que `loading` sea false antes de evaluar (estado inicial).
  if (to.meta.requiresAuth && !authStore.isAuthenticated && !authStore.loading) {
    return { name: "login" };
  }
});

export default router;
