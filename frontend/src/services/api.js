/**
 * Instancia compartida de axios con interceptor que inyecta el ID Token
 * de Firebase en cada petición autenticada.
 *
 * El interceptor llama a `getIdToken()` (que devuelve un token fresco
 * automáticamente, refrescando el caché si está próximo a expirar), de
 * modo que nunca enviamos tokens caducados.
 */
import axios from 'axios'
import { firebaseAuth } from './firebase'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080',
})

api.interceptors.request.use(async (config) => {
  const user = firebaseAuth.currentUser
  if (user) {
    const token = await user.getIdToken()
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
