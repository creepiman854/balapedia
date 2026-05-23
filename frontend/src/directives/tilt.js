/**
 * Directiva v-tilt — efecto "tilt on hover" tipo tilt.js, sin
 * dependencias.
 *
 * Pase final:
 *   - onMove throttled con requestAnimationFrame: aunque el navegador
 *     dispare mousemove a >60Hz, solo aplicamos UN transform por frame.
 *     Sin esto, Firefox encadena reflows en cada movimiento del cursor
 *     y la vista se vuelve a tirones. En Chromium también ayuda, no
 *     solo es FF-specific.
 *   - backface-visibility + will-change desde mount: la capa de
 *     compositing GPU está reservada antes del primer hover; evita
 *     promoción tardía y el "flash" al hacer hover por primera vez.
 *   - cubic-bezier de overshoot en onEnter → zoom con rebote rápido.
 *
 * Uso:
 *   <div v-tilt>...</div>
 *   <div v-tilt="{ max: 15, scale: 1.05, speed: 400 }">...</div>
 */

const DEFAULTS = {
  max: 12,
  scale: 1.06,
  speed: 350,
  perspective: 800,
}

const BOUNCY = 'cubic-bezier(0.34, 1.7, 0.6, 1)'
const SMOOTH = 'cubic-bezier(0.03, 0.98, 0.52, 0.99)'

function getOpts(binding) {
  return { ...DEFAULTS, ...(binding.value || {}) }
}

function baseTransform(opts, rx, ry, scale) {
  return (
    `perspective(${opts.perspective}px) ` +
    `rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) ` +
    `scale(${scale})`
  )
}

function applyTransformFromEvent(el) {
  const opts = el.__tiltOpts
  const ev = el.__tiltPendingEvent
  if (!ev) return
  const rect = el.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const dx = (ev.clientX - cx) / (rect.width / 2)
  const dy = (ev.clientY - cy) / (rect.height / 2)
  const ry = dx * opts.max
  const rx = -dy * opts.max
  el.style.transition = 'transform 80ms linear'
  el.style.transform = baseTransform(opts, rx, ry, opts.scale)
}

function onEnter(e) {
  const el = e.currentTarget
  const opts = el.__tiltOpts
  // Zoom-in con rebote — scale y rotación 0 inicial.
  el.style.transition = `transform 280ms ${BOUNCY}`
  el.style.transform = baseTransform(opts, 0, 0, opts.scale)
  el.__tiltEntered = true
}

/**
 * mousemove → solo guardamos el último evento y programamos un rAF.
 * Si llega otro mousemove antes de ese rAF, se sobreescribe el
 * pendiente y NO se programa otro rAF. Esto garantiza máximo 1
 * recalculo de transform por frame por elemento.
 */
function onMove(e) {
  const el = e.currentTarget
  if (!el.__tiltEntered) return
  el.__tiltPendingEvent = { clientX: e.clientX, clientY: e.clientY }
  if (el.__tiltRaf) return
  el.__tiltRaf = requestAnimationFrame(() => {
    el.__tiltRaf = 0
    if (el.__tiltEntered) applyTransformFromEvent(el)
  })
}

function onLeave(e) {
  const el = e.currentTarget
  const opts = el.__tiltOpts
  if (el.__tiltRaf) {
    cancelAnimationFrame(el.__tiltRaf)
    el.__tiltRaf = 0
  }
  el.__tiltPendingEvent = null
  el.style.transition = `transform ${opts.speed}ms ${SMOOTH}`
  el.style.transform = baseTransform(opts, 0, 0, 1)
  el.__tiltEntered = false
}

export default {
  mounted(el, binding) {
    el.__tiltOpts = getOpts(binding)
    el.__tiltRaf = 0
    el.__tiltEntered = false
    el.style.transformStyle = 'preserve-3d'
    // Forzar capa de compositing GPU desde el inicio — clave para
    // Firefox: sin esto, el primer hover causa promoción de capa y
    // se nota un parpadeo/jank.
    el.style.backfaceVisibility = 'hidden'
    el.style.willChange = 'transform'
    el.addEventListener('mouseenter', onEnter)
    el.addEventListener('mousemove', onMove)
    el.addEventListener('mouseleave', onLeave)
  },
  updated(el, binding) {
    el.__tiltOpts = getOpts(binding)
  },
  unmounted(el) {
    if (el.__tiltRaf) cancelAnimationFrame(el.__tiltRaf)
    el.removeEventListener('mouseenter', onEnter)
    el.removeEventListener('mousemove', onMove)
    el.removeEventListener('mouseleave', onLeave)
    delete el.__tiltOpts
    delete el.__tiltEntered
    delete el.__tiltRaf
    delete el.__tiltPendingEvent
  },
}
