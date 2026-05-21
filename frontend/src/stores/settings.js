/**
 * Store de preferencias de usuario (Pinia).
 *
 * Persiste en localStorage bajo `bala_settings` — lectura síncrona en
 * el constructor para evitar parpadeo del efecto CRT entre el primer
 * render y la hidratación del store.
 *
 * `crt` controla el filtro SVG aplicado al shell de la app (barrel warp
 * + aberración cromática + líneas de escaneo).
 * `jokerColumns` controla la rejilla de la vista de jokers (0 = auto).
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'bala_settings'

const DEFAULTS = {
  crt: true,
  jokerColumns: 0,
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...DEFAULTS }
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULTS }
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const initial = loadFromStorage()

  const crt = ref(initial.crt)
  const jokerColumns = ref(initial.jokerColumns)

  // Auto-persistencia
  watch(
    [crt, jokerColumns],
    () => {
      try {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            crt: crt.value,
            jokerColumns: jokerColumns.value,
          }),
        )
      } catch {
        /* almacenamiento no disponible — ignorar */
      }
    },
    { deep: false },
  )

  function setCrt(value) {
    crt.value = !!value
  }
  function setJokerColumns(value) {
    jokerColumns.value = Number(value) || 0
  }

  return {
    crt,
    jokerColumns,
    setCrt,
    setJokerColumns,
  }
})
