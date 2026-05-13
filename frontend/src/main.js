import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Inicializa el listener de auth ANTES de montar la app.
// El store mantiene loading=true hasta que Firebase determine si hay
// sesión activa (puede tardar 100-300ms tras refresh de página).
const authStore = useAuthStore()
authStore.init()

app.mount('#app')
