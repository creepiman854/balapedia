/**
 * Presets visuales por vista / sub-vista. Dos capas:
 *
 *   1. SHADER PRESETS — parámetros para el fragment shader del fondo
 *      (BalatroBackground.vue). Se interpolan al cambiar de preset.
 *
 *   2. SPARKLE CONFIGS — configuración de la capa de destellos
 *      (SparkleOverlay.vue): pequeños cuadrados que se mueven, rotan
 *      y centellean sobre el shader. Solo aplica a tarot/planet/spectral.
 *
 * Convención: los nombres de preset son lowercase. Las vistas llaman
 * a `bgStore.setPreset('jokers' | 'tarot' | 'planet' | 'spectral')`.
 */

// ────────────────────────────────────────────────────────────────
//  SHADER PRESETS
// ────────────────────────────────────────────────────────────────

// Jokers — rojo + azul + teal oscuro (idéntico al menú principal)
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

// Tarot — morados
export const TAROT_PRESET = {
  spinRotation: 0.15,
  spinSpeed: 2.0,
  spinAmount: 0,
  spinEase: 1.0,
  contrast: 3.2,
  lighting: 0.45,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.471, 0.341, 0.604, 1.0], // morado claro #78579A
  colour2: [0.2, 0.149, 0.271, 1.0],   // púrpura #332645
  colour3: [0.086, 0.086, 0.137, 1.0], // morado oscuro #161623
}

// Planet — grises azulados
export const PLANET_PRESET = {
  spinRotation: 0.18,
  spinSpeed: 2.2,
  spinAmount: 0,
  spinEase: 1.0,
  contrast: 3.5,
  lighting: 0.4,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.173, 0.235, 0.243, 1.0], // gris claro #2C3C3E
  colour2: [0.102, 0.145, 0.153, 1.0], // gris normal #1A2527
  colour3: [0.067, 0.102, 0.11, 1.0],  // gris oscuro #111A1C
}

// Spectral — azules
export const SPECTRAL_PRESET = {
  spinRotation: 0.16,
  spinSpeed: 2.3,
  spinAmount: 0,
  spinEase: 1.0,
  contrast: 3.6,
  lighting: 0.5,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.216, 0.506, 1.0, 1.0],   // azul claro #3781FF
  colour2: [0.122, 0.333, 0.714, 1.0], // azul oscuro #1F55B6
  colour3: [0.035, 0.11, 0.212, 1.0],  // azul marino #091C36
}

// Default: arranca con el de Jokers (es el "menú principal" estético).
export const DEFAULT_PRESET = JOKERS_PRESET

export const BG_PRESETS = {
  default: DEFAULT_PRESET,
  jokers: JOKERS_PRESET,
  tarot: TAROT_PRESET,
  planet: PLANET_PRESET,
  spectral: SPECTRAL_PRESET,
}

export function resolvePreset(name) {
  return BG_PRESETS[name] || BG_PRESETS.default
}

// ────────────────────────────────────────────────────────────────
//  SPARKLE CONFIGS (capa de destellos sobre el shader)
// ────────────────────────────────────────────────────────────────
//
// Cada destello es un cuadradito que:
//   · se desplaza con vx/vy aleatorios dentro de speedRange
//   · rota con rotationSpeed aleatoria
//   · "centellea" modulando size y alpha con un sin(twinklePhase)
//   · vive `lifetimeMs` ms y luego se respawnea (suaviza con fade-in/out)
//
// Para Planet, además, ocasionalmente se spawnea una "estrella fugaz"
// que cruza la pantalla rápido con una pequeña estela.
//
// Tamaños SIEMPRE pequeños (2–6 px CSS) — el efecto es sutil.

const PLANET_SHOOTING_STAR = {
  // ~3-4 por minuto = ~1/1000 por frame a 60 fps.
  spawnChancePerFrame: 1 / 1000,
  speedRange: [9, 14],     // px/frame (mucho más rápido que los normales)
  sizeRange: [8, 16],
  lifetimeMs: 2500,
  trailLength: 14,
  // Las estrellas fugaces toman color de la paleta de planet.
  colors: ['#FFDA96', '#9ED4DF', '#FFFFFF'],
}

export const SPARKLE_CONFIGS = {
  // Vistas sin destellos.
  default: null,
  jokers: null,

  // TAROT — destellos medio rápidos, 3 colores.
  tarot: {
    count: 55,
    sizeRange: [8, 16],
    speedRange: [0.15, 0.5],          // px/frame
    rotationSpeedRange: [-0.02, 0.02],
    twinkleSpeedRange: [0.015, 0.04],
    lifetimeMsRange: [2000, 5000],
    baseAlphaRange: [0.55, 0.95],
    colors: ['#B19AC6', '#FFFFFF', '#F3C667'],
    shootingStar: null,
  },

  // SPECTRAL — destellos lentos, 2 colores (sin morado).
  spectral: {
    count: 40,
    sizeRange: [8, 16],
    speedRange: [0.05, 0.2],
    rotationSpeedRange: [-0.015, 0.015],
    twinkleSpeedRange: [0.008, 0.02],
    lifetimeMsRange: [5000, 10000],
    baseAlphaRange: [0.5, 0.9],
    colors: ['#FFFFFF', '#F3C667'],
    shootingStar: null,
  },

  // PLANET — destellos lentos (como spectral) + estrellas fugaces.
  planet: {
    count: 40,
    sizeRange: [8, 16],
    speedRange: [0.05, 0.2],
    rotationSpeedRange: [-0.015, 0.015],
    twinkleSpeedRange: [0.008, 0.02],
    lifetimeMsRange: [5000, 10000],
    baseAlphaRange: [0.5, 0.9],
    colors: ['#FFDA96', '#9ED4DF', '#FFFFFF'],
    shootingStar: PLANET_SHOOTING_STAR,
  },
}

export function resolveSparkles(name) {
  return SPARKLE_CONFIGS[name] ?? null
}
