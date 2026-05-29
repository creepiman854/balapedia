/**
 * Servicio de sincronización de achievements con Steam.
 *
 * Envuelve `POST /api/me/steam-sync`, el endpoint que orquesta:
 *
 *   1. Recupera los achievements del usuario desde la Steam Web API
 *      (GetPlayerAchievements + GetUserStatsForGame).
 *   2. Por cada achievement con `achieved=1`, llama a
 *      `unlock_achievement_by_code` que aplica:
 *        a) cascade genérica por shared unlock_factor → desbloquea los
 *           Unlockables que comparten el mismo factor (ej. Ante Up!
 *           desbloquea Showman).
 *        b) special resolvers para BAL_23 (Rule Breaker → challenge decks),
 *           BAL_29 (Completionist → todos los items con factor),
 *           BAL_30 (Completionist+ → Gold Sticker en todos los mazos),
 *           BAL_31 (Completionist++ → Gold Sticker en todos los jokers).
 *
 * Toda la lógica de cascade vive server-side, así que esta función
 * frontend es simplemente "dispara y maneja el resultado".
 *
 * El backend traduce cada subclase de SteamApiError a un status code
 * distinto (400/502/503/504) con `error` semántico y `message` legible.
 * Aquí preservamos `error.response.data` para que el caller pueda
 * mostrar el mensaje exacto del backend al usuario.
 */
import { api } from './api'

/**
 * Dispara el sync. Si el usuario tiene `steam_id` vinculado, devuelve
 * el resumen del sync (newly_unlocked, cascadas, sticker applications…).
 * Si no, el backend devuelve 400 `steam_not_linked` y aquí lo dejamos
 * propagar — la UI sabrá redirigir al flow de vinculación.
 *
 * @returns {Promise<SteamSyncResult>} shape definido en el backend
 *   `steam_sync_endpoint._serialize_sync_result`. Tipos principales:
 *   {
 *     user_id, steam_id,
 *     started_at, completed_at, last_steam_sync_at,
 *     summary: {
 *       steam_achievements_received,
 *       steam_achievements_achieved,
 *       newly_unlocked_count,
 *       already_unlocked_count,
 *       total_items_cascaded,
 *       total_sticker_applications,
 *     },
 *     newly_unlocked: [
 *       { id, steam_api_name, name, cascaded_items: [...],
 *         cascaded_sticker_count, notes }
 *     ],
 *     unknown_apinames: string[],
 *   }
 */
export async function syncSteamAchievements() {
  const { data } = await api.post('/api/me/steam-sync')
  return data
}

/**
 * Mensaje legible por el usuario para un error del sync.
 *
 * El backend ya devuelve `message` semántico en data.message para los
 * errores que tiene sentido mostrar tal cual (steam_profile_private,
 * steam_rate_limited, steam_timeout…). Para errores no esperados
 * (Network Error, 500…) caemos a un texto genérico.
 *
 * @param {Error} err  AxiosError del sync.
 * @returns {{ code: string, message: string }} código semántico + texto.
 */
export function describeSyncError(err) {
  // 401 = sesión caducada — el caller debería abrir el AuthModal.
  if (err?.response?.status === 401) {
    return { code: 'unauthorized', message: 'Session expired. Please log in again.' }
  }
  // Backend con respuesta semántica.
  const data = err?.response?.data
  if (data?.error) {
    return {
      code: data.error,
      message: data.message || `Error: ${data.error}`,
    }
  }
  // Sin response = problema de red / backend caído.
  if (!err?.response) {
    return {
      code: 'network_error',
      message: 'Could not connect to the backend. Is Flask running?',
    }
  }
  // 5xx no clasificado.
  return {
    code: 'unknown_error',
    message: err.message || 'Unknown error while syncing with Steam.',
  }
}
