/**
 * Servicio de jokers.
 *
 * Consume los endpoints reales del backend de Balapedia:
 *   - GET /api/jokers           — catálogo público (sin auth)
 *   - GET /api/me/jokers        — catálogo + overlay del usuario logueado
 *
 * Ambos devuelven el mismo shape paginado:
 *   { items, page, per_page, total, total_pages }
 *
 * En /api/me/jokers cada item incluye además:
 *   - unlocked_for_me: bool
 *   - unlocked_at: ISO timestamp | null
 *   - highest_stake_order: 1..8 | null
 *
 * Cuando el usuario está autenticado pedimos siempre /api/me/jokers para
 * conseguir el overlay; cuando no, /api/jokers (los items vienen sin
 * campos de progreso → tratamos todo como "desbloqueado para que se vea").
 *
 * El interceptor de `src/services/api.js` ya inyecta el ID Token de Firebase
 * en cada petición autenticada, así que aquí no hace falta tocar headers.
 */
import { api } from './api'

/**
 * Recolecta TODAS las páginas de jokers en una sola lista.
 *
 * El backend cappa `per_page` a 100; pedimos en bloques de 100 hasta que
 * `total_pages` se agote. Para 150 jokers son 2 requests, asumible.
 * Si en el futuro queremos paginación cliente-lado (scroll infinito,
 * páginas en URL), exponer también `fetchJokersPage(page, perPage)`.
 *
 * @param {object} [opts]
 * @param {boolean} [opts.authenticated]  Pide /api/me/jokers en vez de /api/jokers.
 * @param {string}  [opts.rarity]         Filtro UPPERCASE: COMMON | UNCOMMON | RARE | LEGENDARY.
 * @returns {Promise<Array<object>>}      Lista plana de jokers.
 */
export async function fetchAllJokers({ authenticated = false, rarity } = {}) {
  const path = authenticated ? '/api/me/jokers' : '/api/jokers'
  const params = { per_page: 100, page: 1 }
  if (rarity) params.rarity = rarity

  const first = await api.get(path, { params })
  let items = [...first.data.items]
  const totalPages = first.data.total_pages || 1

  // Páginas restantes en paralelo (max 100 jokers/p → 2 reqs para 150 items).
  if (totalPages > 1) {
    const rest = await Promise.all(
      Array.from({ length: totalPages - 1 }, (_, i) =>
        api.get(path, { params: { ...params, page: i + 2 } }),
      ),
    )
    for (const r of rest) items = items.concat(r.data.items)
  }
  return items
}

/**
 * Detalle de un joker concreto.
 * @param {number} id
 * @returns {Promise<object>}
 */
export async function fetchJokerById(id) {
  const { data } = await api.get(`/api/jokers/${id}`)
  return data
}

/**
 * Resumen agregado del usuario actual (counts/percent por tipo, gold
 * stickers, achievements, last_steam_sync). Requiere sesión.
 * Útil para dashboard de perfil; aquí lo dejamos expuesto por
 * conveniencia.
 *
 * @returns {Promise<object>}
 */
export async function fetchMySummary() {
  const { data } = await api.get('/api/me/summary')
  return data
}
