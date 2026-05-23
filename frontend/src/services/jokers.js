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
import { api } from './api'

/**
 * Recolecta TODAS las páginas de jokers en una sola lista.
 * @param {object} [opts]
 * @param {boolean} [opts.authenticated]
 * @param {string}  [opts.rarity]
 * @returns {Promise<Array<object>>}
 */
export async function fetchAllJokers({ authenticated = false, rarity } = {}) {
  const path = authenticated ? '/api/me/jokers' : '/api/jokers'
  const params = { per_page: 100, page: 1 }
  if (rarity) params.rarity = rarity

  const first = await api.get(path, { params })
  let items = [...first.data.items]
  const totalPages = first.data.total_pages || 1

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
 * Resumen agregado del usuario actual.
 * @returns {Promise<object>}
 */
export async function fetchMySummary() {
  const { data } = await api.get('/api/me/summary')
  return data
}

/**
 * Marca manualmente un joker como desbloqueado para el usuario actual.
 *
 * BACKEND PENDIENTE: requiere endpoint nuevo `POST /api/me/unlocks` con
 * body `{ unlockable_id: <int>, unlocked: <bool> }`. Crea o actualiza
 * la fila correspondiente en `user_unlocks` para el usuario del token.
 *
 * Sugerencia de implementación (Flask, en `app/api/me.py`):
 *
 *   @me_progress_bp.route("/unlocks", methods=["POST"])
 *   @require_auth
 *   def set_my_unlock():
 *       payload = request.get_json() or {}
 *       unlockable_id = payload.get("unlockable_id")
 *       unlocked = bool(payload.get("unlocked", True))
 *       # ...validar que el unlockable existe...
 *       row = UserUnlock.query.filter_by(
 *           user_id=g.user.id, unlockable_id=unlockable_id
 *       ).first()
 *       if not row:
 *           row = UserUnlock(
 *               user_id=g.user.id, unlockable_id=unlockable_id,
 *           )
 *           db.session.add(row)
 *       row.unlocked = unlocked
 *       row.unlocked_at = func.now() if unlocked else None
 *       db.session.commit()
 *       return jsonify({"ok": True})
 *
 * @param {number} jokerId
 * @returns {Promise<void>}
 */
export async function unlockJoker(jokerId) {
  await api.post('/api/me/unlocks', { unlockable_id: jokerId, unlocked: true })
}

/**
 * Desmarca un joker (rollback manual). Útil para testing.
 * @param {number} jokerId
 */
export async function relockJoker(jokerId) {
  await api.post('/api/me/unlocks', { unlockable_id: jokerId, unlocked: false })
}
