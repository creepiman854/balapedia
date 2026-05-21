<!--
  CrtEffects.vue
  Capas visuales que viven detrás del contenido principal:
    · `bg-layer`  → imagen de fondo Balatro + overlay oscuro + ruido pixel
    · `bg-cards`  → cartas flotantes generadas en mount (18 piezas)
    · `crt-lens`  → viñeta de esquinas (curvatura simulada)
    · `crt-overlay` → líneas de escaneo
    · `<svg>` con los filtros `crt-warp` (barrel) y `crt-ca` (aberración).
      Se aplican como `filter` sobre #app cuando settings.crt = true
      (clase `crt-enabled` controlada desde App.vue).

  El barrel map se genera en canvas al montar y se inyecta en el filtro
  con `<feImage>`. Esto evita tener un PNG aparte y mantiene el script
  autocontenido.
-->
<template>
  <!-- Definiciones SVG fuera de pantalla -->
  <svg
    style="position: absolute; width: 0; height: 0; overflow: hidden; pointer-events: none"
    aria-hidden="true"
  >
    <defs>
      <!-- Aberración cromática (separación RGB) -->
      <filter
        id="crt-ca"
        x="-3%"
        y="-3%"
        width="106%"
        height="106%"
        color-interpolation-filters="sRGB"
      >
        <feColorMatrix
          in="SourceGraphic"
          type="matrix"
          values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"
          result="redCh"
        />
        <feOffset in="redCh" dx="3" dy="0" result="redOff" />
        <feColorMatrix
          in="SourceGraphic"
          type="matrix"
          values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0"
          result="greenCh"
        />
        <feColorMatrix
          in="SourceGraphic"
          type="matrix"
          values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0"
          result="blueCh"
        />
        <feOffset in="blueCh" dx="-3" dy="0" result="blueOff" />
        <feBlend in="redOff" in2="greenCh" mode="screen" result="rg" />
        <feBlend in="rg" in2="blueOff" mode="screen" />
      </filter>

      <!-- Barrel distortion: feDisplacementMap usando un mapa inyectado en JS -->
      <filter
        id="crt-warp"
        x="-4%"
        y="-4%"
        width="108%"
        height="108%"
        filterUnits="objectBoundingBox"
        primitiveUnits="objectBoundingBox"
        color-interpolation-filters="sRGB"
      >
        <feImage
          ref="warpMapImg"
          id="crtWarpMapImg"
          result="warpMap"
          preserveAspectRatio="none"
          x="0"
          y="0"
          width="1"
          height="1"
        />
        <feDisplacementMap
          in="SourceGraphic"
          in2="warpMap"
          scale="0.032"
          xChannelSelector="R"
          yChannelSelector="G"
          color-interpolation-filters="sRGB"
        />
      </filter>
    </defs>
  </svg>

  <div class="bg-layer" />
  <div ref="bgCards" class="bg-cards" />
  <div v-show="enabled" class="crt-lens" />
  <div v-show="enabled" class="crt-overlay" />
</template>

<script setup>
import { onMounted, ref } from 'vue'

defineProps({
  enabled: { type: Boolean, default: true },
})

const bgCards = ref(null)
const warpMapImg = ref(null)

function spawnBgCards() {
  if (!bgCards.value) return
  const container = bgCards.value
  container.innerHTML = ''
  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#a855f7']
  for (let i = 0; i < 18; i++) {
    const el = document.createElement('div')
    el.className = 'bg-card'
    const c = colors[Math.floor(Math.random() * colors.length)]
    el.style.left = `${Math.random() * 100}%`
    el.style.bottom = `-80px`
    el.style.width = `${28 + Math.random() * 30}px`
    el.style.height = `${40 + Math.random() * 40}px`
    el.style.borderColor = `${c}18`
    el.style.background = `${c}05`
    el.style.animationDuration = `${18 + Math.random() * 30}s`
    el.style.animationDelay = `${-Math.random() * 40}s`
    container.appendChild(el)
  }
}

/**
 * Construye un mapa de desplazamiento barrel en canvas y lo expone como
 * data URL para que `<feImage>` lo use como fuente del feDisplacementMap.
 *
 * Cada píxel del mapa codifica un desplazamiento (R = X, G = Y):
 *   dx = nx · K · r² ;  dy = ny · K · r²
 * con K controlando la curvatura. Los bordes se estiran hacia fuera,
 * imitando la curvatura de una tele de tubo.
 */
function buildBarrelMap() {
  const SIZE = 512
  const K = 0.22
  const c = document.createElement('canvas')
  c.width = c.height = SIZE
  const ctx = c.getContext('2d')
  const img = ctx.createImageData(SIZE, SIZE)
  const d = img.data
  const maxD = K * 2

  for (let py = 0; py < SIZE; py++) {
    for (let px = 0; px < SIZE; px++) {
      const nx = (px / SIZE) * 2 - 1
      const ny = (py / SIZE) * 2 - 1
      const r2 = nx * nx + ny * ny
      const dx = nx * K * r2
      const dy = ny * K * r2
      const i = (py * SIZE + px) * 4
      d[i] = Math.max(0, Math.min(255, Math.round(128 + (dx / maxD) * 127)))
      d[i + 1] = Math.max(0, Math.min(255, Math.round(128 + (dy / maxD) * 127)))
      d[i + 2] = 0
      d[i + 3] = 255
    }
  }
  ctx.putImageData(img, 0, 0)
  return c.toDataURL('image/png')
}

onMounted(() => {
  spawnBgCards()
  const mapUrl = buildBarrelMap()
  const el = warpMapImg.value
  if (el) {
    el.setAttribute('href', mapUrl)
    try {
      el.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', mapUrl)
    } catch {
      /* navegadores modernos no necesitan xlink */
    }
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  // Imagen de fondo Balatro — colocar en src/assets/images/balatro-bg.png
  // Si no existe el archivo, se ve solo el overlay oscuro.
  background: url('@/assets/images/balatro-bg.png') center / cover no-repeat fixed;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(10, 18, 22, 0.78);
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    opacity: 0.35;
    pointer-events: none;
  }
}

.bg-cards {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  overflow: hidden;
}

:deep(.bg-card) {
  position: absolute;
  width: 40px;
  height: 56px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 3px;
  background: rgba(58, 80, 85, 0.06);
  animation: bgDrift linear infinite;
}

.crt-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.03) 2px,
    rgba(0, 0, 0, 0.03) 4px
  );
}

.crt-lens {
  position: fixed;
  inset: 0;
  z-index: 9997;
  pointer-events: none;
  background:
    radial-gradient(ellipse at 0% 0%, rgba(0, 0, 0, 0.55) 0%, transparent 42%),
    radial-gradient(ellipse at 100% 0%, rgba(0, 0, 0, 0.55) 0%, transparent 42%),
    radial-gradient(ellipse at 0% 100%, rgba(0, 0, 0, 0.55) 0%, transparent 42%),
    radial-gradient(ellipse at 100% 100%, rgba(0, 0, 0, 0.55) 0%, transparent 42%),
    radial-gradient(ellipse at 50% 50%, transparent 50%, rgba(0, 0, 0, 0.25) 100%);
}
</style>
