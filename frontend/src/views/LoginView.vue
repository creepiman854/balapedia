<template>
  <div class="login-view">
    <h1>{{ isSignup ? 'Crear cuenta' : 'Iniciar sesión' }}</h1>

    <form @submit.prevent="handleEmailSubmit">
      <label>
        Email
        <input v-model="email" type="email" required autocomplete="email" />
      </label>
      <label>
        Contraseña
        <input
          v-model="password"
          type="password"
          required
          minlength="6"
          :autocomplete="isSignup ? 'new-password' : 'current-password'"
        />
      </label>
      <button type="submit" :disabled="loading">
        {{ loading ? 'Cargando...' : (isSignup ? 'Registrarme' : 'Entrar') }}
      </button>
    </form>

    <div class="divider">o</div>

    <button class="google-btn" @click="handleGoogleLogin" :disabled="loading">
      Continuar con Google
    </button>

    <button class="link" type="button" @click="isSignup = !isSignup">
      {{ isSignup ? '¿Ya tienes cuenta? Inicia sesión' : '¿No tienes cuenta? Crea una' }}
    </button>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const { error } = storeToRefs(authStore)

const email = ref('')
const password = ref('')
const isSignup = ref(false)
const loading = ref(false)

async function handleEmailSubmit() {
  loading.value = true
  try {
    if (isSignup.value) {
      await authStore.signupWithEmail(email.value, password.value)
    } else {
      await authStore.loginWithEmail(email.value, password.value)
    }
    router.push({ name: 'profile' })
  } catch (e) {
    // Error ya guardado en authStore.error
  } finally {
    loading.value = false
  }
}

async function handleGoogleLogin() {
  loading.value = true
  try {
    await authStore.loginWithGoogle()
    router.push({ name: 'profile' })
  } catch (e) {
    // Error ya guardado en authStore.error
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-view {
  max-width: 400px;
  margin: 3rem auto;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
}
input {
  padding: 0.5rem;
  font-size: 1rem;
}
button {
  padding: 0.75rem;
  font-size: 1rem;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.divider {
  text-align: center;
  color: #888;
  font-size: 0.85rem;
}
.google-btn {
  background: #fff;
  border: 1px solid #ccc;
}
.link {
  background: none;
  border: none;
  color: #1e90ff;
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.9rem;
}
.error {
  color: #c00;
  background: #fee;
  padding: 0.5rem;
  border-radius: 4px;
  text-align: center;
}
</style>
