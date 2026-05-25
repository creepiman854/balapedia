/**
 * Servicio de Colección.
 *
 * Endpoints consumidos (todos públicos, sin auth):
 *   - GET /api/decks
 *   - GET /api/vouchers
 *   - GET /api/booster-packs
 *   - GET /api/card-modifiers?modifier_type=ENHANCEMENT|EDITION|SEAL
 *
 * No hay equivalente `/api/me/*` para ninguno. Cuando exista (overlay
 * de "qué decks tengo Gold Sticker", "qué vouchers he usado"…), basta
 * con duplicar las funciones aquí con el path autenticado.
 *
 * Forma de los items (heredan de Unlockable):
 *   id, type, item_number, name, description, image_url,
 *   unlock_condition, wiki_url, unlock_factor
 *   + campos propios de cada subclase:
 *     - Deck:        (sin extras, todo viene del padre)
 *     - Voucher:     voucher_tier ('BASE' | 'UPGRADED')
 *     - BoosterPack: pack_type ('ARCANA'|...), size ('NORMAL'|'JUMBO'|'MEGA'), cost
 *     - CardModifier (no es subclase de Unlockable, tabla flat):
 *         modifier_type ('ENHANCEMENT' | 'EDITION' | 'SEAL'), name, description
 *
 * Errores: envolvemos los AxiosError en Error con status + mensaje del
 * backend para diagnosticar a la primera (igual que services/consumables.js).
 */
import { api } from './api'

function wrapError(e, contextPath) {
  if (e.response) {
    const status = e.response.status
    const data = e.response.data || {}
    const detail =
      (data.details && JSON.stringify(data.details)) ||
      data.message ||
      data.error ||
      e.response.statusText ||
      `HTTP ${status}`
    const err = new Error(`${contextPath} → ${status}: ${detail}`)
    err.cause = e
    return err
  }
  if (e.request) {
    return new Error(`${contextPath} → sin respuesta del backend (¿flask corriendo en :5000?)`)
  }
  return e
}

/**
 * Reintenta UNA vez con back-off si la primera llamada falla con 500.
 * Pensado para el cold-start del backend: a veces la primera request
 * después de levantar Flask falla por timing (auth + DB warm-up) y
 * un segundo intento ~700 ms después funciona sin problema.
 * Errores que no son 500 (4xx, network) NO se reintentan — son
 * deterministas y un retry no los va a arreglar.
 */
async function withColdStartRetry(fn) {
  try {
    return await fn()
  } catch (e) {
    const is500 = e?.response?.status === 500
    if (!is500) throw e
    await new Promise((r) => setTimeout(r, 700))
    return await fn()
  }
}

/**
 * Helper paginador. Pide la primera página y, si hay más, las restantes
 * en paralelo. Devuelve la lista concatenada de `items`.
 */
async function fetchAllPages(path, extraParams = {}, contextLabel = null) {
  const ctx = contextLabel ?? path
  const params = { per_page: 100, page: 1, ...extraParams }
  try {
    const first = await withColdStartRetry(() => api.get(path, { params }))
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
  } catch (e) {
    throw wrapError(e, ctx)
  }
}

// ── Decks ─────────────────────────────────────────────────────────
/**
 * Si `authenticated` es true se pide /api/me/decks (con overlay
 * `unlocked_for_me`); si no, /api/decks (público, sin overlay).
 *
 * Es el único sub-tab con overlay autenticado a día de hoy — vouchers,
 * booster-packs y card-modifiers no tienen equivalente /api/me/*
 * todavía, así que la vista los trata como locked-por-defecto cuando
 * tienen unlock method no-default (ver `isItemLocked`).
 */
export async function fetchAllDecks({ authenticated = false } = {}) {
  const path = authenticated ? '/api/me/decks' : '/api/decks'
  return fetchAllPages(path)
}

// ── Vouchers ──────────────────────────────────────────────────────
export async function fetchAllVouchers() {
  return fetchAllPages('/api/vouchers')
}

// ── Booster Packs ─────────────────────────────────────────────────
/**
 * Devuelve TODOS los booster packs. La tabla `booster_pack` tiene
 * UNA fila por combinación `(pack_type, size)` — con la seed actual
 * son ~15 filas. La vista los agrupa por `pack_type` y muestra los 3
 * tamaños (NORMAL/JUMBO/MEGA) por cada clase.
 *
 * Si en el futuro se modela "variantes visuales" por combo (ej. 4
 * imágenes distintas para ARCANA NORMAL), o el shape cambia, este
 * fetch sigue valiendo — solo cambia la lógica de presentación.
 */
export async function fetchAllBoosterPacks() {
  return fetchAllPages('/api/booster-packs')
}

// ── Card Modifiers ────────────────────────────────────────────────
/**
 * @param {string} modifierType  ENHANCEMENT | EDITION | SEAL
 */
export async function fetchCardModifiers(modifierType) {
  return fetchAllPages(
    '/api/card-modifiers',
    { modifier_type: modifierType },
    `/api/card-modifiers?modifier_type=${modifierType}`,
  )
}

/**
 * Trae TODOS los card modifiers en una sola request (sin filtro de tipo)
 * y los agrupa por `modifier_type` en el cliente.
 *
 * Antes hacíamos 3 requests en paralelo (una por tipo), pero el plan
 * de hosting actual tiene `max_user_connections=5` y al sumarse a las
 * otras 3 del CollectionView (decks/vouchers/packs) podían llegar 6
 * conexiones simultáneas → 1226 OperationalError del pool MySQL → 500
 * al frontend. Una request única evita el problema y, además, es más
 * eficiente porque el backend solo abre UN cursor.
 *
 * @returns {Promise<{enhancements: Array, editions: Array, seals: Array}>}
 */
export async function fetchAllCardModifiers() {
  const all = await fetchAllPages('/api/card-modifiers')
  const grouped = { enhancements: [], editions: [], seals: [] }
  for (const item of all) {
    const type = String(item.modifier_type || '').toUpperCase()
    if (type === 'ENHANCEMENT') grouped.enhancements.push(item)
    else if (type === 'EDITION') grouped.editions.push(item)
    else if (type === 'SEAL') grouped.seals.push(item)
  }
  return grouped
}

// ── Manual unlock ─────────────────────────────────────────────────
/**
 * Marca un Unlockable como desbloqueado para el usuario actual.
 * Endpoint compartido para jokers/decks/vouchers/booster-packs —
 * todos son subclases de Unlockable, por lo que comparten id namespace
 * para POST /api/me/unlocks { unlockable_id, unlocked }.
 *
 * NOTA: Card Modifiers (Enhancement/Edition/Seal) NO son Unlockable,
 * son tabla flat, así que esta función no aplica a ellos. La vista
 * ya evita que aparezcan como locked, así que el botón ni se renderiza.
 *
 * @param {number} unlockableId
 */
export async function unlockItem(unlockableId) {
  await api.post('/api/me/unlocks', { unlockable_id: unlockableId, unlocked: true })
}
