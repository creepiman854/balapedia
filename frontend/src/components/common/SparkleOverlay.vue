<!--
  Capa de destellos sobre el shader.

  Renderiza pequeños cuadrados que:
    · se desplazan con vx/vy aleatorios.
    · rotan a velocidad aleatoria.
    · "centellean" — modulamos size y alpha con un seno desfasado.
    · nacen, viven `lifetimeMs` y mueren con fade-in/out suave.
    · al morir uno, spawneamos otro para mantener la cuenta del preset.

  Preset planet: además de los destellos lentos comunes, hay una
  probabilidad por frame de spawnear una "estrella fugaz" — cuadrado
  más grande, mucho más rápido, con cola de N posiciones anteriores
  (trail). 3-4 por minuto a 60 fps.

  Transición entre presets: cuando cambia `bgStore.currentPreset`,
  actualizamos `activeConfig`. Los destellos viejos NO se borran de
  golpe; cada uno termina su lifetime y se reemplaza por uno del nuevo
  preset (su lifecycle natural produce un cross-fade implícito).

  Performance:
    · Canvas 2D, no WebGL → mismo coste en todos los navegadores.
    · DPR acotado a 1.5 (igual que BalatroBackground).
    · Pausa con visibilitychange — sin esto Firefox sigue corriendo
      el rAF a baja frecuencia consumiendo CPU.
    · pointer-events: none → nunca intercepta clicks.
-->
<template>
  <canvas ref="canvasRef" class="sparkle-overlay" aria-hidden="true" />
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useBackgroundStore } from '@/stores/background'
import { resolveSparkles } from '@/constants/backgrounds'

const canvasRef = ref(null)

const bgStore = useBackgroundStore()
const { currentPreset } = storeToRefs(bgStore)

let ctx = null
let rafId = null
let resizeHandler = null
let visibilityHandler = null
let paused = false

// Dimensiones en CSS pixels (lo que ven los cálculos). El canvas
// internamente trabaja a dpr para nitidez.
let canvasW = 0
let canvasH = 0
let dpr = 1

const particles = []
const shootingStars = []
let activeConfig = null

// ── Utilidades ────────────────────────────────────────────────────
function rng(min, max) {
  return min + Math.random() * (max - min)
}
function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)]
}

// ── Spawning ──────────────────────────────────────────────────────
function spawnParticle(cfg, nowMs) {
  // Dirección aleatoria con speed dentro del rango (independiente por eje).
  const angle = rng(0, Math.PI * 2)
  const speed = rng(cfg.speedRange[0], cfg.speedRange[1])
  return {
    x: rng(0, canvasW),
    y: rng(0, canvasH),
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    rotation: rng(0, Math.PI * 2),
    rotSpeed: rng(cfg.rotationSpeedRange[0], cfg.rotationSpeedRange[1]),
    baseSize: rng(cfg.sizeRange[0], cfg.sizeRange[1]),
    color: pick(cfg.colors),
    twinklePhase: rng(0, Math.PI * 2),
    twinkleSpeed: rng(cfg.twinkleSpeedRange[0], cfg.twinkleSpeedRange[1]),
    baseAlpha: rng(cfg.baseAlphaRange[0], cfg.baseAlphaRange[1]),
    bornAt: nowMs,
    lifetimeMs: rng(cfg.lifetimeMsRange[0], cfg.lifetimeMsRange[1]),
    currentAlpha: 0,
    currentSize: 0,
  }
}

function spawnShootingStar(cfg, nowMs) {
  // Spawneamos en la mitad superior, ángulo principalmente hacia abajo
  // (60°..120° desde la horizontal positiva, o sea ~45° de cono central).
  const angle = rng(Math.PI / 3, (2 * Math.PI) / 3)
  const speed = rng(cfg.speedRange[0], cfg.speedRange[1])
  return {
    x: rng(0, canvasW),
    y: -10,
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    rotation: angle,
    size: rng(cfg.sizeRange[0], cfg.sizeRange[1]),
    color: pick(cfg.colors),
    bornAt: nowMs,
    lifetimeMs: cfg.lifetimeMs,
    trail: [],
    trailLength: cfg.trailLength,
    currentAlpha: 0,
  }
}

// ── Update tick ───────────────────────────────────────────────────
function updateParticle(p, nowMs) {
  p.x += p.vx
  p.y += p.vy
  // Wrap por los bordes — no queremos que desaparezcan en el aire.
  if (p.x < -10) p.x = canvasW + 10
  if (p.x > canvasW + 10) p.x = -10
  if (p.y < -10) p.y = canvasH + 10
  if (p.y > canvasH + 10) p.y = -10
  p.rotation += p.rotSpeed
  p.twinklePhase += p.twinkleSpeed
  // Fade-in al nacer (500 ms) + fade-out al morir (500 ms).
  const age = nowMs - p.bornAt
  const fadeIn = Math.min(1, age / 500)
  const fadeOut = Math.min(1, (p.lifetimeMs - age) / 500)
  const lifeFactor = Math.max(0, Math.min(fadeIn, fadeOut))
  const tw = 0.5 + 0.5 * Math.sin(p.twinklePhase)
  p.currentSize = p.baseSize * (0.5 + 0.5 * tw)
  p.currentAlpha = p.baseAlpha * lifeFactor * (0.55 + 0.45 * tw)
}

function updateShootingStar(s, nowMs) {
  s.trail.push({ x: s.x, y: s.y })
  if (s.trail.length > s.trailLength) s.trail.shift()
  s.x += s.vx
  s.y += s.vy
  const age = nowMs - s.bornAt
  const fadeIn = Math.min(1, age / 100)
  const fadeOut = Math.min(1, (s.lifetimeMs - age) / 300)
  s.currentAlpha = Math.max(0, Math.min(fadeIn, fadeOut))
}

function update(nowMs) {
  // Particles regulares
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]
    if (nowMs - p.bornAt >= p.lifetimeMs) {
      particles.splice(i, 1)
    } else {
      updateParticle(p, nowMs)
    }
  }
  if (activeConfig) {
    while (particles.length < activeConfig.count) {
      particles.push(spawnParticle(activeConfig, nowMs))
    }
  }

  // Shooting stars (solo planet por ahora)
  for (let i = shootingStars.length - 1; i >= 0; i--) {
    const s = shootingStars[i]
    if (
      nowMs - s.bornAt >= s.lifetimeMs ||
      s.x < -60 ||
      s.x > canvasW + 60 ||
      s.y > canvasH + 60
    ) {
      shootingStars.splice(i, 1)
    } else {
      updateShootingStar(s, nowMs)
    }
  }
  if (activeConfig?.shootingStar) {
    if (Math.random() < activeConfig.shootingStar.spawnChancePerFrame) {
      shootingStars.push(spawnShootingStar(activeConfig.shootingStar, nowMs))
    }
  }
}

// ── Render ────────────────────────────────────────────────────────
function draw() {
  if (!ctx) return
  ctx.clearRect(0, 0, canvasW, canvasH)

  // Particles
  for (const p of particles) {
    if (p.currentAlpha <= 0.01) continue
    ctx.save()
    ctx.globalAlpha = p.currentAlpha
    ctx.fillStyle = p.color
    ctx.translate(p.x, p.y)
    ctx.rotate(p.rotation)
    const half = p.currentSize / 2
    ctx.fillRect(-half, -half, p.currentSize, p.currentSize)
    ctx.restore()
  }

  // Shooting stars + estela
  for (const s of shootingStars) {
    if (s.currentAlpha <= 0.01) continue
    // Estela: cada posición previa con alpha creciente (más reciente = más visible).
    for (let i = 0; i < s.trail.length; i++) {
      const t = s.trail[i]
      const f = (i + 1) / s.trail.length          // 0..1
      const a = s.currentAlpha * 0.6 * f
      const sz = s.size * (0.4 + 0.6 * f)
      ctx.save()
      ctx.globalAlpha = a
      ctx.fillStyle = s.color
      ctx.translate(t.x, t.y)
      ctx.rotate(s.rotation)
      ctx.fillRect(-sz / 2, -sz / 2, sz, sz)
      ctx.restore()
    }
    // Cabeza
    ctx.save()
    ctx.globalAlpha = s.currentAlpha
    ctx.fillStyle = s.color
    ctx.translate(s.x, s.y)
    ctx.rotate(s.rotation)
    ctx.fillRect(-s.size / 2, -s.size / 2, s.size, s.size)
    ctx.restore()
  }
}

function loop(nowMs) {
  if (paused) return
  update(nowMs)
  draw()
  rafId = requestAnimationFrame(loop)
}

// ── Watch del preset ──────────────────────────────────────────────
watch(currentPreset, (name) => {
  activeConfig = resolveSparkles(name)
  // No tocamos `particles` ni `shootingStars`: las viejas cumplen su
  // lifetime y mueren solas, las nuevas se spawnean con el preset
  // entrante. Cross-fade implícito.
})

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  if (!ctx) return

  dpr = Math.min(window.devicePixelRatio || 1, 1.5)

  resizeHandler = () => {
    const w = window.innerWidth
    const h = window.innerHeight
    canvas.width = Math.floor(w * dpr)
    canvas.height = Math.floor(h * dpr)
    canvas.style.width = w + 'px'
    canvas.style.height = h + 'px'
    // Trabajamos en coordenadas CSS pixels — multiplicamos por dpr al final.
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    canvasW = w
    canvasH = h
  }
  window.addEventListener('resize', resizeHandler)
  resizeHandler()

  activeConfig = resolveSparkles(currentPreset.value)

  visibilityHandler = () => {
    if (document.hidden) {
      paused = true
      if (rafId) cancelAnimationFrame(rafId)
    } else if (paused) {
      paused = false
      rafId = requestAnimationFrame(loop)
    }
  }
  document.addEventListener('visibilitychange', visibilityHandler)

  rafId = requestAnimationFrame(loop)
})

onBeforeUnmount(() => {
  if (rafId) cancelAnimationFrame(rafId)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (visibilityHandler) document.removeEventListener('visibilitychange', visibilityHandler)
  particles.length = 0
  shootingStars.length = 0
})
</script>

<style scoped>
.sparkle-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  /* Encima del shader (z:0) y debajo del contenido (#app-content z:10). */
  z-index: 1;
  pointer-events: none;
}
</style>
