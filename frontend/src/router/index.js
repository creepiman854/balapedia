/**
 * Balapedia Router.
 *
 * Main views (Jokers / Consumables / Achievements / Collection).
 * `/` redirects to `/jokers` as the default view.
 * Login and Profile are handled via the global AuthModal.
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
    path: "/consumables",
    name: "consumables",
    component: () => import("@/views/ConsumablesView.vue"),
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
