<!--
  Fondo dinámico de la app: shader WebGL idéntico al fondo del menú
  principal de Balatro. Los parámetros (colores, velocidad, contraste,
  …) son `uniform`s en lugar de `#define`, así pueden interpolarse
  suavemente cuando la vista cambia de preset.

  Cómo funciona:
    1. Al montar, compilamos el shader una sola vez y obtenemos las
       locations de cada uniform.
    2. Mantenemos en memoria los uniforms en 3 estados:
         · `current` — los valores que se pasan al GPU en cada frame.
         · `from`    — desde dónde está animando ahora mismo.
         · `to`      — hacia dónde va.
    3. Watch del store: al cambiar `currentPreset` arrancamos una
       transición; en cada frame del render loop lerpamos `current` =
       lerp(from, to, easeOutCubic(t)) y subimos al GPU.

  Fallback: si el navegador no devuelve contexto WebGL (extraño en 2026
  pero posible en modos restringidos), el canvas se queda transparente
  y la app sigue funcionando con el color de fondo de body.

  Compatibilidad: probado en Chromium, Firefox y WebKit. Evitamos
  cualquier API moderna (color-mix, filter SVG sobre HTML, etc.) — todo
  es WebGL 1.0 + Canvas 2D fallback.
-->
<template>
  <canvas
    ref="glCanvas"
    class="balatro-bg"
    aria-hidden="true"
  />
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useBackgroundStore } from '@/stores/background'
import { resolvePreset } from '@/constants/backgrounds'

const TRANSITION_MS = 700

// ── Shaders ─────────────────────────────────────────────────────────
// Vertex: pasa coords directamente. Fragment: el efecto Balatro
// completo, pero con uniforms en vez de #define.
const VS_SOURCE = `
  attribute vec2 a_position;
  void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
`

const FS_SOURCE = `
  precision highp float;

  uniform vec2  u_resolution;
  uniform float u_time;

  uniform float u_spinRotation;
  uniform float u_spinSpeed;
  uniform float u_spinAmount;
  uniform float u_spinEase;
  uniform float u_contrast;
  uniform float u_lighting;
  uniform float u_pixelFilter;
  uniform float u_isRotate;     // 0.0 = static, 1.0 = animated
  uniform vec4  u_colour1;
  uniform vec4  u_colour2;
  uniform vec4  u_colour3;

  vec4 effect(vec2 screenSize, vec2 screen_coords) {
    float pixel_size = length(screenSize.xy) / u_pixelFilter;
    vec2 uv = (floor(screen_coords.xy * (1.0 / pixel_size)) * pixel_size
              - 0.5 * screenSize.xy) / length(screenSize.xy);
    float uv_len = length(uv);

    float speed = u_spinRotation * u_spinEase * 0.2;
    speed = mix(speed, u_time * speed, u_isRotate);
    speed += 302.2;

    float new_pixel_angle = atan(uv.y, uv.x) + speed
                            - u_spinEase * 20.0
                              * (u_spinAmount * uv_len
                                 + (1.0 - u_spinAmount));
    vec2 mid = (screenSize.xy / length(screenSize.xy)) / 2.0;
    uv = vec2(uv_len * cos(new_pixel_angle) + mid.x,
              uv_len * sin(new_pixel_angle) + mid.y) - mid;

    uv *= 30.0;
    speed = u_time * u_spinSpeed;
    vec2 uv2 = vec2(uv.x + uv.y);

    for (int i = 0; i < 5; i++) {
      uv2 += sin(max(uv.x, uv.y)) + uv;
      uv  += 0.5 * vec2(cos(5.1123314 + 0.353 * uv2.y + speed * 0.131121),
                        sin(uv2.x - 0.113 * speed));
      uv  -= 1.0 * cos(uv.x + uv.y) - 1.0 * sin(uv.x * 0.711 - uv.y);
    }

    float contrast_mod = 0.25 * u_contrast + 0.5 * u_spinAmount + 1.2;
    float paint_res = min(2.0, max(0.0, length(uv) * 0.035 * contrast_mod));
    float c1p = max(0.0, 1.0 - contrast_mod * abs(1.0 - paint_res));
    float c2p = max(0.0, 1.0 - contrast_mod * abs(paint_res));
    float c3p = 1.0 - min(1.0, c1p + c2p);
    float light = (u_lighting - 0.2) * max(c1p * 5.0 - 4.0, 0.0)
                  + u_lighting * max(c2p * 5.0 - 4.0, 0.0);

    return (0.3 / u_contrast) * u_colour1
           + (1.0 - 0.3 / u_contrast)
             * (u_colour1 * c1p
                + u_colour2 * c2p
                + vec4(c3p * u_colour3.rgb, c3p * u_colour1.a))
           + light;
  }

  void main() {
    gl_FragColor = effect(u_resolution.xy, gl_FragCoord.xy);
  }
`

// ── Estado del componente ───────────────────────────────────────────
const glCanvas = ref(null)

const bgStore = useBackgroundStore()
const { currentPreset } = storeToRefs(bgStore)

let gl = null
let program = null
let animationFrameId = null
let resizeHandler = null
let visibilityHandler = null
let paused = false

// Uniforms locations cache para no llamar getUniformLocation cada frame.
const ulocs = {}

// Estados de la transición.
//   transitionState: 'idle' | 'pending' | 'active'
//     - idle:    sin transición en curso.
//     - pending: setPreset ya cambió fromParams/toParams pero todavía
//                no hemos capturado el `nowMs` de inicio. Lo hacemos
//                en el PRIMER rAF callback siguiente, así nos
//                aseguramos de que `transitionStartMs` y los `nowMs`
//                posteriores vienen del MISMO reloj.
//     - active:  transición en curso, lerpeando cada frame.
//
// Esto evita un bug observado: si `transitionStart` se captura con
// `performance.now()` desde dentro del watch y `nowMs` viene del
// rAF callback, en algunas situaciones (tab background, reentrant
// rAFs en Firefox) el delta crece más rápido de lo esperado y la
// transición parece "acelerarse" con el tiempo.
let fromParams = { ...resolvePreset(currentPreset.value) }
let toParams = { ...resolvePreset(currentPreset.value) }
let currentParams = { ...resolvePreset(currentPreset.value) }
let transitionState = 'idle'
let transitionStartMs = 0

function compileShader(type, source) {
  const shader = gl.createShader(type)
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error('[BalatroBackground] shader compile error:', gl.getShaderInfoLog(shader))
    gl.deleteShader(shader)
    return null
  }
  return shader
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

function lerp(a, b, t) {
  return a + (b - a) * t
}
function lerpVec4(a, b, t) {
  return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t), lerp(a[3], b[3], t)]
}

function tickTransition(nowMs) {
  if (transitionState === 'idle') return

  // Primer tick desde startTransition: capturamos el `nowMs` exacto
  // del rAF callback como inicio. Garantiza que `elapsed` se calcula
  // sobre el mismo reloj que los siguientes ticks.
  if (transitionState === 'pending') {
    transitionStartMs = nowMs
    transitionState = 'active'
  }

  const elapsed = nowMs - transitionStartMs
  const t = Math.min(1, Math.max(0, elapsed / TRANSITION_MS))
  const eased = easeOutCubic(t)
  currentParams = {
    spinRotation: lerp(fromParams.spinRotation, toParams.spinRotation, eased),
    spinSpeed: lerp(fromParams.spinSpeed, toParams.spinSpeed, eased),
    spinAmount: lerp(fromParams.spinAmount, toParams.spinAmount, eased),
    spinEase: lerp(fromParams.spinEase, toParams.spinEase, eased),
    contrast: lerp(fromParams.contrast, toParams.contrast, eased),
    lighting: lerp(fromParams.lighting, toParams.lighting, eased),
    pixelFilter: lerp(fromParams.pixelFilter, toParams.pixelFilter, eased),
    isRotate: toParams.isRotate, // booleano, no se lerpea
    colour1: lerpVec4(fromParams.colour1, toParams.colour1, eased),
    colour2: lerpVec4(fromParams.colour2, toParams.colour2, eased),
    colour3: lerpVec4(fromParams.colour3, toParams.colour3, eased),
  }
  if (t >= 1) {
    // Forzamos coincidencia exacta para evitar drift por errores de
    // float al final de la transición.
    currentParams = { ...toParams, colour1: [...toParams.colour1], colour2: [...toParams.colour2], colour3: [...toParams.colour3] }
    fromParams = { ...toParams, colour1: [...toParams.colour1], colour2: [...toParams.colour2], colour3: [...toParams.colour3] }
    transitionState = 'idle'
  }
}

function uploadUniforms(timeSec) {
  gl.uniform1f(ulocs.u_time, timeSec)
  gl.uniform1f(ulocs.u_spinRotation, currentParams.spinRotation)
  gl.uniform1f(ulocs.u_spinSpeed, currentParams.spinSpeed)
  gl.uniform1f(ulocs.u_spinAmount, currentParams.spinAmount)
  gl.uniform1f(ulocs.u_spinEase, currentParams.spinEase)
  gl.uniform1f(ulocs.u_contrast, currentParams.contrast)
  gl.uniform1f(ulocs.u_lighting, currentParams.lighting)
  gl.uniform1f(ulocs.u_pixelFilter, currentParams.pixelFilter)
  gl.uniform1f(ulocs.u_isRotate, currentParams.isRotate ? 1.0 : 0.0)
  gl.uniform4f(ulocs.u_colour1, ...currentParams.colour1)
  gl.uniform4f(ulocs.u_colour2, ...currentParams.colour2)
  gl.uniform4f(ulocs.u_colour3, ...currentParams.colour3)
}

// Iniciar transición desde currentParams hacia los nuevos.
// El tiempo de arranque NO se captura aquí: se captura en el
// primer rAF callback siguiente (ver tickTransition), para garantizar
// que ambos relojes (start y now) son el mismo.
function startTransition(newParams) {
  fromParams = {
    ...currentParams,
    colour1: [...currentParams.colour1],
    colour2: [...currentParams.colour2],
    colour3: [...currentParams.colour3],
  }
  toParams = {
    ...newParams,
    colour1: [...newParams.colour1],
    colour2: [...newParams.colour2],
    colour3: [...newParams.colour3],
  }
  transitionState = 'pending'
}

watch(currentPreset, (name) => {
  startTransition(resolvePreset(name))
})

onMounted(() => {
  const canvas = glCanvas.value
  if (!canvas) return

  // antialias:false → fondo más pixel-style + mejor rendimiento.
  gl = canvas.getContext('webgl', { antialias: false, alpha: true })
  if (!gl) {
    console.warn('[BalatroBackground] WebGL no disponible — sin fondo animado')
    return
  }

  // Compilar y enlazar.
  const vs = compileShader(gl.VERTEX_SHADER, VS_SOURCE)
  const fs = compileShader(gl.FRAGMENT_SHADER, FS_SOURCE)
  if (!vs || !fs) return
  program = gl.createProgram()
  gl.attachShader(program, vs)
  gl.attachShader(program, fs)
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error('[BalatroBackground] program link error:', gl.getProgramInfoLog(program))
    return
  }
  gl.useProgram(program)

  // Quad fullscreen.
  const buf = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buf)
  gl.bufferData(
    gl.ARRAY_BUFFER,
    new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]),
    gl.STATIC_DRAW,
  )
  const aPos = gl.getAttribLocation(program, 'a_position')
  gl.enableVertexAttribArray(aPos)
  gl.vertexAttribPointer(aPos, 2, gl.FLOAT, false, 0, 0)

  // Cache de uniform locations.
  ulocs.u_resolution = gl.getUniformLocation(program, 'u_resolution')
  ulocs.u_time = gl.getUniformLocation(program, 'u_time')
  ulocs.u_spinRotation = gl.getUniformLocation(program, 'u_spinRotation')
  ulocs.u_spinSpeed = gl.getUniformLocation(program, 'u_spinSpeed')
  ulocs.u_spinAmount = gl.getUniformLocation(program, 'u_spinAmount')
  ulocs.u_spinEase = gl.getUniformLocation(program, 'u_spinEase')
  ulocs.u_contrast = gl.getUniformLocation(program, 'u_contrast')
  ulocs.u_lighting = gl.getUniformLocation(program, 'u_lighting')
  ulocs.u_pixelFilter = gl.getUniformLocation(program, 'u_pixelFilter')
  ulocs.u_isRotate = gl.getUniformLocation(program, 'u_isRotate')
  ulocs.u_colour1 = gl.getUniformLocation(program, 'u_colour1')
  ulocs.u_colour2 = gl.getUniformLocation(program, 'u_colour2')
  ulocs.u_colour3 = gl.getUniformLocation(program, 'u_colour3')

  // Resize. devicePixelRatio acotado a 1.5 (era 2): el shader hace 5
  // iteraciones por píxel en una pantalla retina, lo cual saturaba la
  // GPU en Firefox. A 1.5 el look apenas cambia (sigue siendo pixelado
  // por el u_pixelFilter del propio shader) y baja el coste ~44%.
  resizeHandler = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5)
    const w = Math.floor(window.innerWidth * dpr)
    const h = Math.floor(window.innerHeight * dpr)
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w
      canvas.height = h
    }
    gl.viewport(0, 0, w, h)
    gl.uniform2f(ulocs.u_resolution, w, h)
  }
  window.addEventListener('resize', resizeHandler)
  resizeHandler()

  // Render loop. Aunque rAF pausa con la tab oculta en navegadores
  // modernos, en Firefox a veces sigue corriendo a baja frecuencia
  // (~5Hz) consumiendo CPU. Con `paused` lo cortamos de raíz.
  const t0 = performance.now()
  const render = (now) => {
    if (paused) return
    tickTransition(now)
    uploadUniforms((now - t0) / 1000)
    gl.drawArrays(gl.TRIANGLES, 0, 6)
    animationFrameId = requestAnimationFrame(render)
  }
  animationFrameId = requestAnimationFrame(render)

  visibilityHandler = () => {
    if (document.hidden) {
      paused = true
      if (animationFrameId) cancelAnimationFrame(animationFrameId)
    } else if (paused) {
      paused = false
      animationFrameId = requestAnimationFrame(render)
    }
  }
  document.addEventListener('visibilitychange', visibilityHandler)
})

onBeforeUnmount(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (visibilityHandler) document.removeEventListener('visibilitychange', visibilityHandler)
  if (gl && program) {
    try {
      gl.deleteProgram(program)
    } catch {
      /* contexto perdido — ok */
    }
  }
})
</script>

<style scoped>
.balatro-bg {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 0;
  pointer-events: none;
  /* Sin filtros aplicados sobre el canvas: queremos el shader a pelo. */
}
</style>
