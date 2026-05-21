<!--
  Etiqueta de rareza pixelada.

  Acepta el campo `rarity` tal y como lo devuelve el backend
  ('COMMON' | 'UNCOMMON' | 'RARE' | 'LEGENDARY' — UPPERCASE) y resuelve
  contra el mapa local de constantes. `getRarity` tolera lowercase por si
  en algún sitio se pasa con cualquier casing.
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
  const pad = props.size === 'sm' ? '2px 10px' : '4px 16px'
  const fs = props.size === 'sm' ? '8px' : '9px'
  return {
    display: 'inline-block',
    background: r.value.color,
    color: '#fff',
    fontFamily: "'m6x11plus', monospace",
    fontSize: fs,
    padding: pad,
    clipPath:
      'polygon(0px calc(100% - 8px), 2px calc(100% - 8px), 2px calc(100% - 4px), 4px calc(100% - 4px), 4px calc(100% - 2px), 8px calc(100% - 2px), 8px 100%, calc(100% - 8px) 100%, calc(100% - 8px) calc(100% - 2px), calc(100% - 4px) calc(100% - 2px), calc(100% - 4px) calc(100% - 4px), calc(100% - 2px) calc(100% - 4px), calc(100% - 2px) calc(100% - 8px), 100% calc(100% - 8px), 100% 8px, calc(100% - 2px) 8px, calc(100% - 2px) 4px, calc(100% - 4px) 4px, calc(100% - 4px) 2px, calc(100% - 8px) 2px, calc(100% - 8px) 0px, 8px 0px, 8px 2px, 4px 2px, 4px 4px, 2px 4px, 2px 8px, 0px 8px)',
    letterSpacing: '0.5px',
    textShadow: '1px 1px 0 rgba(0,0,0,0.5)',
    boxShadow: `0 2px 8px ${r.value.glow}`,
  }
})
</script>
