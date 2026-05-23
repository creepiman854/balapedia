/**
 * Presets de parámetros para el shader del fondo (BalatroBackground).
 *
 * Cada preset describe la "atmósfera" visual de una vista o sub-vista:
 *   · spinRotation : velocidad de rotación global
 *   · spinSpeed    : velocidad del oleaje interno
 *   · spinAmount   : profundidad del efecto rotatorio
 *   · spinEase     : curvatura del easing del giro
 *   · contrast     : contraste entre colores
 *   · lighting     : brillo extra en los picos
 *   · pixelFilter  : densidad del pixelado (más alto = más pixelado fino)
 *   · isRotate     : rotación automática activa
 *   · colour1/2/3  : 3 colores principales (RGBA 0..1)
 *
 * Las vistas llaman a `bgStore.setPreset('nombre')` en su onMounted, y
 * el shader interpola suavemente entre el preset anterior y el nuevo
 * durante ~700 ms (ver BalatroBackground.vue).
 */

// Jokers — rojo + azul + teal oscuro (igual al fondo del menú principal de Balatro)
export const JOKERS_PRESET = {
  spinRotation: 0.2,
  spinSpeed: 2.5,
  spinAmount: 0.25,
  spinEase: 1.0,
  contrast: 3.5,
  lighting: 0.4,
  pixelFilter: 745.0,
  isRotate: true,
  colour1: [0.871, 0.267, 0.231, 1.0], // rojo Balatro
  colour2: [0.0, 0.42, 0.706, 1.0],    // azul Balatro
  colour3: [0.086, 0.137, 0.145, 1.0], // teal muy oscuro
}

// Tarot — dorado + púrpura místico (apartado consumibles/tarot)
export const TAROT_PRESET = {
  spinRotation: 0.15,
  spinSpeed: 2.0,
  spinAmount: 0.22,
  spinEase: 1.0,
  contrast: 3.2,
  lighting: 0.45,
  pixelFilter: 745.0,
  isRotate: true,
  colour1: [0.847, 0.690, 0.384, 1.0], // dorado tarot
  colour2: [0.353, 0.176, 0.553, 1.0], // púrpura místico
  colour3: [0.086, 0.063, 0.118, 1.0], // morado muy oscuro
}

// Planet — azul espacial + cian profundo (apartado consumibles/planeta)
export const PLANET_PRESET = {
  spinRotation: 0.18,
  spinSpeed: 2.2,
  spinAmount: 0.25,
  spinEase: 1.0,
  contrast: 3.5,
  lighting: 0.4,
  pixelFilter: 745.0,
  isRotate: true,
  colour1: [0.278, 0.565, 0.631, 1.0], // azul planeta
  colour2: [0.063, 0.235, 0.349, 1.0], // cian profundo
  colour3: [0.024, 0.055, 0.071, 1.0], // azul oscuro
}

// Spectral — azul-violeta inquietante (apartado consumibles/espectral)
export const SPECTRAL_PRESET = {
  spinRotation: 0.16,
  spinSpeed: 2.3,
  spinAmount: 0.3,
  spinEase: 1.0,
  contrast: 3.6,
  lighting: 0.5,
  pixelFilter: 745.0,
  isRotate: true,
  colour1: [0.314, 0.4, 0.647, 1.0],   // azul-violeta
  colour2: [0.243, 0.243, 0.529, 1.0], // indigo
  colour3: [0.031, 0.039, 0.094, 1.0], // casi negro azulado
}

// Default / fallback — usa el de Jokers (es el "menu principal" estético)
export const DEFAULT_PRESET = JOKERS_PRESET

export const BG_PRESETS = {
  default: DEFAULT_PRESET,
  jokers: JOKERS_PRESET,
  tarot: TAROT_PRESET,
  planet: PLANET_PRESET,
  spectral: SPECTRAL_PRESET,
}

/** Devuelve siempre un preset válido, con fallback al default. */
export function resolvePreset(name) {
  return BG_PRESETS[name] || BG_PRESETS.default
}
