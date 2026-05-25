/**
 * Entrada de la app.
 *
 * Orden:
 *   1. Pinia → permite construir los stores antes que el router.
 *   2. Auth store init() → activa el listener de Firebase.
 *   3. Router → sus guards ya pueden esperar a authStore.loading.
 *   4. Directivas globales (tilt).
 *   5. mount.
 *
 * Los estilos globales (Tailwind base + custom SCSS) se importan aquí
 * para que estén disponibles desde el primer render.
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import tilt from './directives/tilt'
import "iconify-icon";

import '@/assets/styles/main.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Directiva global para tarjetas con efecto tilt.
app.directive('tilt', tilt)

// Inicializa el listener de auth ANTES de montar la app.
const authStore = useAuthStore()
authStore.init()

app.mount('#app')
