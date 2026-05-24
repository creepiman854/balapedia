/**
 * Accents (color de acento + glow + label) por tipo de item.
 *
 * Los items del catálogo de Balatro caen en dos "ejes" de color:
 *   - Jokers              → color por rareza (constants/rarity.js)
 *   - Consumables         → color por type   (TAROT / PLANET / SPECTRAL)
 *   - Decks / vouchers /  → más adelante, cuando hagamos sus vistas.
 *     boosters / blinds /
 *     tags / stickers
 *
 * Este módulo unifica el lookup: `getItemAccent(item)` devuelve siempre
 * un objeto `{ color, glow, dark, label }` válido, sin importar si el
 * item es un joker o un consumible.
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

/**
 * Devuelve el accent visual de un item, tolerando los dos shapes
 * (joker con `rarity`, consumible con `type`). Fallback al accent
 * neutro si ni una ni otra propiedad están presentes.
 */
export function getItemAccent(item) {
  if (!item) return DEFAULT_ACCENT
  // Jokers: el accent viene de la rareza.
  if (item.rarity) return getRarity(item.rarity)
  // Consumibles: por type.
  const type = String(item.type || '').toUpperCase()
  if (CONSUMABLE_ACCENTS[type]) return CONSUMABLE_ACCENTS[type]
  return DEFAULT_ACCENT
}

/**
 * Devuelve la etiqueta humana para el "tag" inferior de la card:
 *   - joker: la rareza (Común / Inusual / Raro / Legendario)
 *   - consumible: el type (Arcano / Planeta / Espectral)
 *   - otro: cadena vacía
 */
export function getItemBadgeLabel(item) {
  if (!item) return ''
  if (item.rarity) return getRarity(item.rarity).label
  const acc = CONSUMABLE_ACCENTS[String(item.type || '').toUpperCase()]
  return acc?.label || ''
}
