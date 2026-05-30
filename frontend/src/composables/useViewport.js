/**
 * Composable reactivo con flags `isMobile` y `isTablet` derivados de
 * matchMedia. Refleja los mismos breakpoints SCSS de _mixins.scss:
 *
 *   mobile      → max-width: 599px
 *   tablet-only → 600px ≤ w ≤ 1023px
 *   desktop     → > 1023px  (no flag, es la condición por defecto)
 *
 * Pensado para que la JS del componente sepa cuántas columnas pintar
 * en el grid Y pasar el `col-count` correcto al ItemCard — el arco
 * por fila depende de que JS y CSS estén sincronizados.
 */
import { ref, onMounted, onBeforeUnmount } from "vue";

export function useViewport() {
  const isMobile = ref(false);
  const isTablet = ref(false);

  let mqMobile = null;
  let mqTablet = null;

  function update() {
    isMobile.value = mqMobile?.matches ?? false;
    isTablet.value = mqTablet?.matches ?? false;
  }

  onMounted(() => {
    mqMobile = window.matchMedia("(max-width: 599px)");
    mqTablet = window.matchMedia("(min-width: 600px) and (max-width: 1023px)");
    update();
    mqMobile.addEventListener("change", update);
    mqTablet.addEventListener("change", update);
  });

  onBeforeUnmount(() => {
    mqMobile?.removeEventListener("change", update);
    mqTablet?.removeEventListener("change", update);
  });

  return { isMobile, isTablet };
}
