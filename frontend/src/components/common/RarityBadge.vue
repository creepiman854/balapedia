<!--
  Etiqueta de rareza pixelada.

  El backend devuelve `rarity` en UPPERCASE (JokerRarity enum). El helper
  `getRarity` tolera lower/upper-case por defensa, pero el camino feliz
  es UPPERCASE directo.

  Tamaños:
    sm  → para listados densos.
    md  → tamaño por defecto, panel de detalle y tooltip.
          Subido respecto al pase anterior (era 9px) porque a 9px no
          se leía bien sobre los fondos del shader.
-->
<template>
  <span :style="style">{{ r.label }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { getRarity } from '@/constants/rarity'

const props = defineProps({
  rarity: { type: String, required: true },
  size: { type: String, default: 'md' }, // 'sm' | 'md'
})

const r = computed(() => getRarity(props.rarity))

const style = computed(() => {
  const isSm = props.size === 'sm'
  const pad = isSm ? '3px 12px' : '6px 22px'
  const fs = isSm ? '10px' : '14px'
  return {
    display: 'inline-block',
    background: r.value.color,
    color: '#fff',
    fontFamily: "'m6x11plus', monospace",
    fontSize: fs,
    padding: pad,
    clipPath:
      'polygon(0px calc(100% - 8px), 2px calc(100% - 8px), 2px calc(100% - 4px), 4px calc(100% - 4px), 4px calc(100% - 2px), 8px calc(100% - 2px), 8px 100%, calc(100% - 8px) 100%, calc(100% - 8px) calc(100% - 2px), calc(100% - 4px) calc(100% - 2px), calc(100% - 4px) calc(100% - 4px), calc(100% - 2px) calc(100% - 4px), calc(100% - 2px) calc(100% - 8px), 100% calc(100% - 8px), 100% 8px, calc(100% - 2px) 8px, calc(100% - 2px) 4px, calc(100% - 4px) 4px, calc(100% - 4px) 2px, calc(100% - 8px) 2px, calc(100% - 8px) 0px, 8px 0px, 8px 2px, 4px 2px, 4px 4px, 2px 4px, 2px 8px, 0px 8px)',
    letterSpacing: '0.6px',
    textShadow: '1px 1px 0 rgba(0,0,0,0.55)',
    boxShadow: `0 2px 8px ${r.value.glow}`,
  }
})
</script>
