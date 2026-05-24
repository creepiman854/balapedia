<!--
  Badge pixelado genérico.

  Sustituye a `RarityBadge` (que estaba acoplado al mapa de rarezas de
  jokers). Recibe label/color/glow desde el padre, que sabe cómo
  resolverlos (vía `getItemAccent` o equivalente).

  Para items con rareza el padre pasa el accent de rareza; para
  consumibles, el accent del type. La presentación visual es la misma:
  fondo del color del accent, texto blanco con sombra, clip pixel.
-->
<template>
  <span :style="style">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  color: { type: String, required: true },
  glow: { type: String, default: 'transparent' },
  size: { type: String, default: 'md' }, // 'sm' | 'md'
})

const style = computed(() => {
  const isSm = props.size === 'sm'
  const pad = isSm ? '3px 12px' : '6px 22px'
  const fs = isSm ? '10px' : '14px'
  return {
    display: 'inline-block',
    background: props.color,
    color: '#fff',
    fontFamily: "'m6x11plus', monospace",
    fontSize: fs,
    padding: pad,
    clipPath:
      'polygon(0px calc(100% - 8px), 2px calc(100% - 8px), 2px calc(100% - 4px), 4px calc(100% - 4px), 4px calc(100% - 2px), 8px calc(100% - 2px), 8px 100%, calc(100% - 8px) 100%, calc(100% - 8px) calc(100% - 2px), calc(100% - 4px) calc(100% - 2px), calc(100% - 4px) calc(100% - 4px), calc(100% - 2px) calc(100% - 4px), calc(100% - 2px) calc(100% - 8px), 100% calc(100% - 8px), 100% 8px, calc(100% - 2px) 8px, calc(100% - 2px) 4px, calc(100% - 4px) 4px, calc(100% - 4px) 2px, calc(100% - 8px) 2px, calc(100% - 8px) 0px, 8px 0px, 8px 2px, 4px 2px, 4px 4px, 2px 4px, 2px 8px, 0px 8px)',
    letterSpacing: '0.6px',
    textShadow: '1px 1px 0 rgba(0,0,0,0.55)',
    boxShadow: `0 2px 8px ${props.glow}`,
  }
})
</script>
