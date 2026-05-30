/**
 * Estado UI del header global. Lo usan AppHeader y el composable
 * `useHideHeaderOnScroll` para coordinar el auto-hide del header durante
 * el scroll dentro del contenido principal en móvil.
 *
 * Nota: el ocultado se aplica solo en móvil vía CSS dentro de
 * AppHeader; este store es agnóstico al viewport.
 */
import { defineStore } from "pinia";
import { ref } from "vue";

export const useHeaderStore = defineStore("header", () => {
  const hidden = ref(false);

  function setHidden(value) {
    hidden.value = !!value;
  }

  function show() {
    hidden.value = false;
  }

  return { hidden, setHidden, show };
});
