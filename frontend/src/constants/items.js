/**
 * Helpers compartidos para todos los items del catálogo
 * (jokers, consumibles, decks, vouchers, booster packs, card modifiers).
 *
 *   getItemAccent(item)       → color/glow/dark/label por rareza o type.
 *   getItemBadgeLabel(item)   → etiqueta humana para el badge inferior.
 *   getItemEffectText(item)   → descripción/efecto resuelto entre los
 *                               varios campos posibles del backend.
 *   isAvailableFromStart(item)→ true si el item está desbloqueado por
 *                               defecto al iniciar el juego.
 *   isItemLocked(item, auth)  → resuelve el estado locked unificando
 *                               overlay backend + heurística por
 *                               unlock_condition.
 *
 * Toda la lógica de "qué se ve y qué no" en las vistas pasa por aquí
 * — así jokers, consumibles y colección comparten una única fuente
 * de verdad.
 */

import { getRarity } from './rarity'

export const CONSUMABLE_ACCENTS = {
  TAROT: {
    color: '#D8B062',
    glow: 'rgba(216, 176, 98, 0.5)',
    dark: '#1e1408',
    label: 'Arcano',
  },
  PLANET: {
    color: '#4790A1',
    glow: 'rgba(71, 144, 161, 0.5)',
    dark: '#061418',
    label: 'Planeta',
  },
  SPECTRAL: {
    color: '#5066A5',
    glow: 'rgba(80, 102, 165, 0.5)',
    dark: '#08091a',
    label: 'Espectral',
  },
}

const DEFAULT_ACCENT = {
  color: '#708387',
  glow: 'rgba(112, 131, 135, 0.4)',
  dark: '#1A2A2E',
  label: '',
}

export function getItemAccent(item) {
  if (!item) return DEFAULT_ACCENT
  if (item.rarity) return getRarity(item.rarity)
  const type = String(item.type || '').toUpperCase()
  if (CONSUMABLE_ACCENTS[type]) return CONSUMABLE_ACCENTS[type]
  return DEFAULT_ACCENT
}

export function getItemBadgeLabel(item) {
  if (!item) return ''
  if (item.rarity) return getRarity(item.rarity).label
  const acc = CONSUMABLE_ACCENTS[String(item.type || '').toUpperCase()]
  return acc?.label || ''
}

/**
 * Devuelve el texto del efecto/descripción del item, probando los
 * varios campos posibles del backend (en orden de prioridad):
 *   - `description`  → jokers, decks, vouchers, booster packs.
 *   - `effect`       → card modifiers (Enhancement/Edition/Seal).
 *
 * Vacío si ninguno está poblado. Las vistas hacen el fallback a "—".
 */
export function getItemEffectText(item) {
  if (!item) return ''
  return item.description || item.effect || ''
}

/**
 * Detecta items que están desbloqueados de fábrica.
 * Heurística por string sobre `unlock_condition` y
 * `unlock_factor.description` + `unlock_factor.code`.
 * Match en ES e IN para tolerar ambos idiomas en la BD.
 */
export function isAvailableFromStart(item) {
  if (!item) return false
  const condition = String(
    item.unlock_condition || item.unlock_factor?.description || '',
  ).toLowerCase()
  // Aceptamos varias variantes semánticamente equivalentes que aparecen
  // en la wiki de Balatro: "Available from start", "Unlocked from start",
  // ambas con/sin "the", + traducción ES.
  if (
    condition.includes('available from start') ||
    condition.includes('available from the start') ||
    condition.includes('unlocked from start') ||
    condition.includes('unlocked from the start') ||
    condition.includes('disponible desde el inicio') ||
    condition.includes('desbloqueado desde el inicio')
  ) {
    return true
  }
  const code = String(item.unlock_factor?.code || '').toLowerCase()
  return code === 'available_from_start' || code === 'unlocked_from_start' || code === 'start'
}

/**
 * Decide si un item se muestra como "bloqueado" para el usuario actual.
 *
 *   - Sin sesión               → todo visible (false).
 *   - "Available from start"   → siempre visible (false).
 *   - Con overlay (`unlocked_for_me`) del backend → usa ese flag.
 *   - Sin overlay PERO con un unlock_condition no-trivial → locked.
 *   - Sin overlay y sin unlock_condition → visible.
 *
 * El caso "sin overlay con unlock_condition" cubre vouchers/packs/
 * modifiers, cuyos endpoints públicos no devuelven `unlocked_for_me`.
 * Mejor errar como locked para no enseñar progreso que no tenemos.
 *
 * @param {object} item
 * @param {boolean} isAuthenticated
 * @returns {boolean}
 */
export function isItemLocked(item, isAuthenticated) {
  if (!isAuthenticated) return false
  if (isAvailableFromStart(item)) return false
  if (item && Object.prototype.hasOwnProperty.call(item, 'unlocked_for_me')) {
    return !item.unlocked_for_me
  }
  return !!(item?.unlock_condition || item?.unlock_factor)
}
