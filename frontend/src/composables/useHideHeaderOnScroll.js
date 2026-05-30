/**
 * Composable que vincula un elemento scrollable al store del header
 * para que éste se oculte cuando el usuario hace scroll hacia abajo y
 * vuelva a aparecer al subir.
 *
 * Pensado para los contenedores .grid-scroll / .list-scroll de cada
 * vista. Cada vista llama:
 *
 *   const scrollEl = ref(null);
 *   useHideHeaderOnScroll(scrollEl);
 *   ...
 *   <div class="grid-scroll" ref="scrollEl">...</div>
 *
 * Reglas anti-rebote (pase v5):
 *
 *   · MICRO_DELTA → ignoramos micro-scrolls < 6px (anti-jitter).
 *   · TOP_GUARD → no ocultamos en los primeros 80px del scroll.
 *   · BOTTOM_GUARD → no ocultamos cuando estamos a menos de 120px
 *     del final. Antes, si el contenido era corto, ocultar el header
 *     liberaba alto de viewport y el navegador re-acomodaba el scroll
 *     hacia arriba (porque ya no podía estar tan abajo). Ese ajuste
 *     se interpretaba como "scroll up" → mostrar header → re-ajuste →
 *     ocultar de nuevo → bucle (rebote visible).
 *   · MIN_OVERFLOW → si scrollHeight - clientHeight < 200px (apenas
 *     hay scroll), ni siquiera intentamos ocultar. Es una optimización
 *     extra: cuando la lista cabe casi entera no merece la pena
 *     animar el header.
 *
 * El propio store decide si el header se renderiza oculto — el CSS de
 * AppHeader limita el efecto a viewports móviles vía media queries.
 */
import { onMounted, onBeforeUnmount, watch } from "vue";
import { useHeaderStore } from "@/stores/header";

const MICRO_DELTA = 6;
const TOP_GUARD = 80;
const BOTTOM_GUARD = 120;
const MIN_OVERFLOW_RATIO = 0.35;

// Tiempo aproximado de la animación CSS del header.
const HEADER_TRANSITION_MS = 250;

export function useHideHeaderOnScroll(elRef) {
  const headerStore = useHeaderStore();

  let currentEl = null;
  let lastTop = 0;
  let lockUntil = 0;

  function setHeaderHidden(hidden) {
    if (headerStore.hidden === hidden) return;

    headerStore.setHidden(hidden);

    // Ignora scrolls provocados por el reflow del propio header.
    lockUntil = performance.now() + HEADER_TRANSITION_MS;
  }

  function onScroll() {
    if (!currentEl) return;

    // Ignorar eventos generados por la propia animación.
    if (performance.now() < lockUntil) {
      lastTop = currentEl.scrollTop;
      return;
    }

    const st = currentEl.scrollTop;
    const delta = st - lastTop;

    if (Math.abs(delta) < MICRO_DELTA) {
      lastTop = st;
      return;
    }

    const overflow = currentEl.scrollHeight - currentEl.clientHeight;

    // Si apenas hay scroll, mantener visible.
    if (overflow < currentEl.clientHeight * MIN_OVERFLOW_RATIO) {
      setHeaderHidden(false);
      lastTop = st;
      return;
    }

    if (delta > 0 && st > TOP_GUARD) {
      const remaining = overflow - st;

      if (remaining >= BOTTOM_GUARD) {
        setHeaderHidden(true);
      }
    } else if (delta < 0) {
      setHeaderHidden(false);
    }

    lastTop = st;
  }

  function attach(el) {
    if (currentEl === el) return;

    detach();

    if (!el) return;

    currentEl = el;
    lastTop = el.scrollTop || 0;

    el.addEventListener("scroll", onScroll, {
      passive: true,
    });
  }

  function detach() {
    if (currentEl) {
      currentEl.removeEventListener("scroll", onScroll);
    }

    currentEl = null;
  }

  onMounted(() => attach(elRef.value));

  watch(elRef, (el) => attach(el));

  onBeforeUnmount(() => {
    detach();
    headerStore.show();
  });
}
