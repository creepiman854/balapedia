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
  colour2: [0.0, 0.42, 0.706, 1.0], // azul Balatro
  colour3: [0.086, 0.137, 0.145, 1.0], // teal muy oscuro
};

// Tarot — Réplica del fondo de los sobres Tarot del juego
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
  colour2: [0.2, 0.149, 0.271, 1.0], // púrpura #332645
  colour3: [0.086, 0.086, 0.137, 1.0], // morado oscuro #161623
};

// Planet — Réplica del fondo de los sobres Planeta del juego
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
  colour3: [0.067, 0.102, 0.11, 1.0], // gris oscuro #111A1C
};

// Spectral — Réplica del fondo de los sobres Espectrales del juego
export const SPECTRAL_PRESET = {
  spinRotation: 0.16,
  spinSpeed: 2.3,
  spinAmount: 0,
  spinEase: 1.0,
  contrast: 3.6,
  lighting: 0.5,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.216, 0.506, 1.0, 1.0], // azul claro #3781FF
  colour2: [0.122, 0.333, 0.714, 1.0], // azul oscuro #1F55B6
  colour3: [0.035, 0.11, 0.212, 1.0], // azul marino #091C36
};

// ────────────────────────────────────────────────────────────────
//  Colección — paletas por sub-tab. Valores iniciales — ajusta a
//  gusto cuando los veas en pantalla.
// ────────────────────────────────────────────────────────────────

// Decks — verde mesa de cartas
export const DECKS_PRESET = {
  spinRotation: 0.18,
  spinSpeed: 2.2,
  spinAmount: 0.15,
  spinEase: 1.0,
  contrast: 3.4,
  lighting: 0.4,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.231, 0.435, 0.337, 1.0], // verde mesa #3B6F56
  colour2: [0.118, 0.243, 0.196, 1.0], // verde oscuro #1E3E32
  colour3: [0.039, 0.094, 0.075, 1.0], // casi negro verdoso #0A1813
};

// Booster Packs — naranja / dorado de la tienda
export const BOOSTER_PACKS_PRESET = {
  spinRotation: 0.2,
  spinSpeed: 2.4,
  spinAmount: 0.15,
  spinEase: 1.0,
  contrast: 3.4,
  lighting: 0.45,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.851, 0.498, 0.196, 1.0], // naranja #D97F32
  colour2: [0.467, 0.243, 0.063, 1.0], // naranja oscuro #773E10
  colour3: [0.118, 0.063, 0.024, 1.0], // marrón muy oscuro #1E1006
};

// Vouchers — cian / turquesa "gema"
export const VOUCHERS_PRESET = {
  spinRotation: 0.16,
  spinSpeed: 2.1,
  spinAmount: 0.1,
  spinEase: 1.0,
  contrast: 3.5,
  lighting: 0.42,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.318, 0.643, 0.682, 1.0], // turquesa #51A4AE
  colour2: [0.094, 0.31, 0.353, 1.0], // turquesa oscuro #184F5A
  colour3: [0.024, 0.082, 0.094, 1.0], // azul casi negro #061518
};

// Card modifiers — violeta apagado (enhancement/edition/seal)
export const CARD_MODIFIERS_PRESET = {
  spinRotation: 0.14,
  spinSpeed: 2.0,
  spinAmount: 0.1,
  spinEase: 1.0,
  contrast: 3.3,
  lighting: 0.42,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.42, 0.298, 0.518, 1.0], // violeta apagado #6B4C84
  colour2: [0.184, 0.122, 0.243, 1.0], // violeta oscuro #2F1F3E
  colour3: [0.063, 0.043, 0.094, 1.0], // casi negro morado #100B18
};

// Achievements — rojo "trofeo" con vetas doradas.
export const ACHIEVEMENTS_PRESET = {
  spinRotation: 0.18,
  spinSpeed: 2.3,
  spinAmount: 0.18,
  spinEase: 1.0,
  contrast: 3.5,
  lighting: 0.42,
  pixelFilter: 745.0,
  isRotate: true,
  colour1: [0.937, 0.267, 0.267, 1.0], // rojo trofeo #EF4444
  colour2: [0.498, 0.137, 0.137, 1.0], // rojo oscuro #7F2323
  colour3: [0.118, 0.043, 0.043, 1.0], // casi negro rojizo #1E0B0B
};

// Blinds — tonos carmesí/rojo jefe (#cf3535)
export const BLINDS_PRESET = {
  spinRotation: 0.17,
  spinSpeed: 2.4,
  spinAmount: 0.15,
  spinEase: 1.0,
  contrast: 3.5,
  lighting: 0.45,
  pixelFilter: 745.0,
  isRotate: true,
  colour1: [0.812, 0.208, 0.208, 1.0], // rojo carmesí #cf3535
  colour2: [0.451, 0.118, 0.118, 1.0], // carmesí oscuro #731e1e
  colour3: [0.122, 0.031, 0.031, 1.0], // casi negro rojizo #1f0808
};

// Tags — tonos verde esmeralda/neón (#22c55e)
export const TAGS_PRESET = {
  spinRotation: 0.15,
  spinSpeed: 2.1,
  spinAmount: 0.1,
  spinEase: 1.0,
  contrast: 3.4,
  lighting: 0.4,
  pixelFilter: 745.0,
  isRotate: false,
  colour1: [0.133, 0.773, 0.369, 1.0], // verde brillante #22c55e
  colour2: [0.067, 0.384, 0.184, 1.0], // verde bosque #11622f
  colour3: [0.024, 0.125, 0.063, 1.0], // verde casi negro #062010
};

// Default: arranca con el de Jokers (es el "menú principal" estético).
export const DEFAULT_PRESET = JOKERS_PRESET;

export const BG_PRESETS = {
  default: DEFAULT_PRESET,
  jokers: JOKERS_PRESET,
  tarot: TAROT_PRESET,
  planet: PLANET_PRESET,
  spectral: SPECTRAL_PRESET,
  decks: DECKS_PRESET,
  "booster-packs": BOOSTER_PACKS_PRESET,
  vouchers: VOUCHERS_PRESET,
  "card-modifiers": CARD_MODIFIERS_PRESET,
  achievements: ACHIEVEMENTS_PRESET,
  blinds: BLINDS_PRESET,
  tags: TAGS_PRESET,
};

export function resolvePreset(name) {
  return BG_PRESETS[name] || BG_PRESETS.default;
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
  speedRange: [9, 14], // px/frame (mucho más rápido que los normales)
  sizeRange: [8, 16],
  lifetimeMs: 2500,
  trailLength: 14,
  // Las estrellas fugaces toman color de la paleta de planet.
  colors: ["#FFDA96", "#9ED4DF", "#FFFFFF"],
};

export const SPARKLE_CONFIGS = {
  // Vistas sin destellos.
  default: null,
  jokers: null,

  // Colección
  decks: null,
  "booster-packs": null,
  vouchers: null,
  "card-modifiers": null,
  blinds: null,
  tags: null,

  // Achievements — sin destellos (la vista ya tiene su propio "shimmer"
  // sobre los iconos desbloqueados; añadir más capa visual molestaría).
  achievements: null,

  // TAROT — destellos medio rápidos, 3 colores.
  tarot: {
    count: 55,
    sizeRange: [8, 16],
    speedRange: [0.15, 0.5], // px/frame
    rotationSpeedRange: [-0.02, 0.02],
    twinkleSpeedRange: [0.015, 0.04],
    lifetimeMsRange: [2000, 5000],
    baseAlphaRange: [0.55, 0.95],
    colors: ["#B19AC6", "#FFFFFF", "#F3C667"],
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
    colors: ["#FFFFFF", "#F3C667"],
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
    colors: ["#FFDA96", "#9ED4DF", "#FFFFFF"],
    shootingStar: PLANET_SHOOTING_STAR,
  },
};

export function resolveSparkles(name) {
  return SPARKLE_CONFIGS[name] ?? null;
}
