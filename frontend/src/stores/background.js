/**
 * Store del fondo dinámico.
 *
 * Cada vista llama a `setPreset(name)` en su onMounted con el nombre del
 * preset que le toca (jokers, tarot, planet, spectral…). El componente
 * BalatroBackground reacciona al cambio interpolando suavemente los
 * uniforms del shader entre el preset anterior y el nuevo.
 *
 * No se persiste — el preset depende de la vista actual, no de
 * preferencias del usuario.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { BG_PRESETS } from '@/constants/backgrounds'

export const useBackgroundStore = defineStore('background', () => {
  const currentPreset = ref('default')

  function setPreset(name) {
    if (BG_PRESETS[name]) {
      currentPreset.value = name
    } else {
      console.warn(`[background] preset desconocido "${name}", manteniendo el actual`)
    }
  }

  return { currentPreset, setPreset }
})
