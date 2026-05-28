/**
 * Store de preferencias visuales (Pinia).
 *
 * Persiste en localStorage bajo `bala_settings`. Cargamos en el constructor
 * de forma síncrona para evitar parpadeo entre el primer render y la
 * hidratación.
 *
 * Estado:
 *   crtIntensity        0..1   Intensidad del efecto CRT (slider del modal).
 *                              0 = totalmente desactivado, 1 = máximo.
 *   musicEnabled        bool   Toggle ON/OFF de la música ambiente
 *                              (la fuente de audio se conectará en otra rama).
 *   musicVolume         0..1   Volumen cuando música está activa.
 *   gridColumns         5..15  Columnas del grid de Jokers.
 *   showSpoiledLocked   bool   Modo spoiler: si false (default) los items
 *                              bloqueados se ven con el asset oficial
 *                              "locked"; si true, se ve la imagen real
 *                              atenuada (desaturada + brillo reducido).
 *                              Solo afecta a Jokers / Vouchers / Decks —
 *                              los demás tipos no tienen asset locked y
 *                              su estado bloqueado no aplica.
 *
 * COLUMNS_MIN / COLUMNS_MAX son constantes a nivel de módulo, NO valores
 * del store. La razón es importante: si se devuelven dentro del setup
 * store, `storeToRefs` las envuelve como refs y al destructurar en un
 * componente quedan como ref objects que `<input :min>` recibe como
 * objeto en lugar de número — ese era el bug del slider que se "saltaba
 * al máximo" en el primer cambio.
 */
import { defineStore } from "pinia";
import { ref, watch } from "vue";

const STORAGE_KEY = "bala_settings";

export const COLUMNS_MIN = 5;
export const COLUMNS_MAX = 15;

const DEFAULTS = {
  crtIntensity: 0.5,
  musicEnabled: false,
  musicVolume: 0.4,
  gridColumns: 7,
  showSpoiledLocked: false,
};

function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw);
    return {
      crtIntensity: clamp(Number(parsed.crtIntensity ?? DEFAULTS.crtIntensity), 0, 1),
      musicEnabled: !!parsed.musicEnabled,
      musicVolume: clamp(Number(parsed.musicVolume ?? DEFAULTS.musicVolume), 0, 1),
      gridColumns: clamp(
        Math.round(parsed.gridColumns ?? DEFAULTS.gridColumns),
        COLUMNS_MIN,
        COLUMNS_MAX,
      ),
      // `showSpoiledLocked` puede no existir en localStorage si el usuario
      // ya tenía la app abierta antes del release de Fase 2: nullish-
      // coalescing al default. El cast a bool absorbe valores legacy.
      showSpoiledLocked: !!(parsed.showSpoiledLocked ?? DEFAULTS.showSpoiledLocked),
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export const useSettingsStore = defineStore("settings", () => {
  const initial = loadFromStorage();

  const crtIntensity = ref(initial.crtIntensity);
  const musicEnabled = ref(initial.musicEnabled);
  const musicVolume = ref(initial.musicVolume);
  const gridColumns = ref(initial.gridColumns);
  const showSpoiledLocked = ref(initial.showSpoiledLocked);

  watch([crtIntensity, musicEnabled, musicVolume, gridColumns, showSpoiledLocked], () => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          crtIntensity: crtIntensity.value,
          musicEnabled: musicEnabled.value,
          musicVolume: musicVolume.value,
          gridColumns: gridColumns.value,
          showSpoiledLocked: showSpoiledLocked.value,
        }),
      );
    } catch {
      /* almacenamiento no disponible — ignorar */
    }
  });

  function setCrtIntensity(v) {
    crtIntensity.value = clamp(Number(v) || 0, 0, 1);
  }
  function setMusicEnabled(v) {
    musicEnabled.value = !!v;
  }
  function setMusicVolume(v) {
    musicVolume.value = clamp(Number(v) || 0, 0, 1);
  }
  function setGridColumns(v) {
    gridColumns.value = clamp(Math.round(Number(v) || COLUMNS_MIN), COLUMNS_MIN, COLUMNS_MAX);
  }
  function setShowSpoiledLocked(v) {
    showSpoiledLocked.value = !!v;
  }

  return {
    crtIntensity,
    musicEnabled,
    musicVolume,
    gridColumns,
    showSpoiledLocked,
    setCrtIntensity,
    setMusicEnabled,
    setMusicVolume,
    setGridColumns,
    setShowSpoiledLocked,
  };
});
