/**
 * Router de Balapedia.
 *
 * Rutas principales del diseño (Jokers / Consumibles / Logros / Colección).
 * `/` redirige a `/jokers` que es la vista por defecto.
 * El login y el perfil ahora se gestionan mediante un Modal global.
 */
import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/jokers" },

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
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
