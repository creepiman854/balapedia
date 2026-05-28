/**
 * Servicio de jokers.
 *
 * Consume los endpoints reales del backend de Balapedia:
 *   - GET /api/jokers           — catálogo público (sin auth)
 *   - GET /api/me/jokers        — catálogo + overlay del usuario logueado
 *   - POST /api/me/unlocks      — marca/desmarca un unlockable manualmente
 *
 * Para el POST manual usamos la convención que ya sigue el resto del
 * backend (UserUnlock por unlockable_id). El backend lo recibe como
 * `{ unlockable_id, unlocked }` y crea/actualiza la fila.
 *
 * El interceptor de `src/services/api.js` inyecta el ID Token de Firebase
 * en cada petición autenticada, así que aquí no hace falta tocar headers.
 */
import { api } from "./api";

/**
 * Recolecta TODAS las páginas de jokers en una sola lista.
 * @param {object} [opts]
 * @param {boolean} [opts.authenticated]
 * @param {string}  [opts.rarity]
 * @returns {Promise<Array<object>>}
 */
export async function fetchAllJokers({ authenticated = false, rarity } = {}) {
  const path = authenticated ? "/api/me/jokers" : "/api/jokers";
  const params = { per_page: 100, page: 1 };
  if (rarity) params.rarity = rarity;

  const first = await api.get(path, { params });
  let items = [...first.data.items];
  const totalPages = first.data.total_pages || 1;

  if (totalPages > 1) {
    for (let page = 2; page <= totalPages; page++) {
      const r = await api.get(path, {
        params: { ...params, page },
      });

      items = items.concat(r.data.items);
    }
  }
  return items;
}

/**
 * Detalle de un joker concreto.
 * @param {number} id
 * @returns {Promise<object>}
 */
export async function fetchJokerById(id) {
  const { data } = await api.get(`/api/jokers/${id}`);
  return data;
}

/**
 * Resumen agregado del usuario actual.
 * @returns {Promise<object>}
 */
export async function fetchMySummary() {
  const { data } = await api.get("/api/me/summary");
  return data;
}

/**
 * Marca manualmente un joker como desbloqueado para el usuario actual.
 *
 * Llama al endpoint compartido `POST /api/me/unlocks` con
 * `{ unlockable_id, unlocked: true }`. El backend hace el upsert
 * idempotente vía `services/unlocks_service.set_unlock_for_user` —
 * el mismo punto de entrada que usará el sync de Steam, así que un
 * joker que ya estuviese desbloqueado por Steam permanece igual.
 *
 * Respuesta esperada (200): `{ ok, unlocked_for_me, unlocked_at }`.
 * El caller puede usar esos campos para mutar la fila local sin
 * tener que re-fetchear todo el catálogo.
 *
 * @param {number} jokerId
 * @returns {Promise<void>}
 */
export async function unlockJoker(jokerId) {
  await api.post("/api/me/unlocks", { unlockable_id: jokerId, unlocked: true });
}

/**
 * Desmarca un joker (rollback manual). Útil para testing y para un
 * futuro botón "ocultar este joker como completado" en la UI.
 *
 * @param {number} jokerId
 */
export async function relockJoker(jokerId) {
  await api.post("/api/me/unlocks", { unlockable_id: jokerId, unlocked: false });
}
