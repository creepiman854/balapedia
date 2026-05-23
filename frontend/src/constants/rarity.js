/**
 * Constantes visuales por rareza de joker.
 *
 * Las KEYS son las que devuelve el backend (UPPERCASE, ver
 * `app/api/schemas.py` → `JokerSchema.rarity = fields.Enum(JokerRarity)`).
 * Los valores son puramente UI: etiqueta en español + colores para
 * acentos, bordes y glows.
 */

export const RARITY = {
  COMMON: {
    id: 'COMMON',
    label: 'Común',
    color: '#4a9fd4',
    dark: '#0d2538',
    glow: 'rgba(74, 159, 212, 0.4)',
  },
  UNCOMMON: {
    id: 'UNCOMMON',
    label: 'Inusual',
    color: '#3abf5e',
    dark: '#0a2414',
    glow: 'rgba(58, 191, 94, 0.4)',
  },
  RARE: {
    id: 'RARE',
    label: 'Raro',
    color: '#e84040',
    dark: '#2a0808',
    glow: 'rgba(232, 64, 64, 0.4)',
  },
  LEGENDARY: {
    id: 'LEGENDARY',
    label: 'Legendario',
    color: '#c060e0',
    dark: '#1e0830',
    glow: 'rgba(192, 96, 224, 0.5)',
  },
}

/**
 * Devuelve la metadata de rareza tolerando mayúsculas/minúsculas y valores
 * no reconocidos (fallback a COMMON para no romper la UI).
 */
export function getRarity(raw) {
  if (!raw) return RARITY.COMMON
  const key = String(raw).toUpperCase()
  return RARITY[key] || RARITY.COMMON
}

/**
 * Orden numérico para los selects de ordenamiento por rareza.
 */
export const RARITY_ORDER = {
  COMMON: 0,
  UNCOMMON: 1,
  RARE: 2,
  LEGENDARY: 3,
}
