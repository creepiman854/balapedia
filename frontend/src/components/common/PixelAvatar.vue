<!--
  Avatar pixelado para usuarios autenticados con Google o Steam.
  Para login por email no muestra nada (no hay foto asociada).
-->
<template>
  <div v-if="scheme" :title="scheme.title" :style="containerStyle">
    <span :style="initialStyle">{{ initial }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  user: { type: Object, default: () => null },
  size: { type: Number, default: 38 },
})

const SCHEMES = {
  google: { bg: '#4285f4', border: '#6aa3f7', title: 'Cuenta Google' },
  steam: { bg: '#1b4a6b', border: '#66c0f4', title: 'Cuenta Steam' },
}

// Detecta el método de login del user del store; ignora si es email puro.
const scheme = computed(() => {
  if (!props.user) return null
  const method = props.user.method || (props.user.steam_id ? 'steam' : null)
  if (!method) return null
  return SCHEMES[method]
})

const initial = computed(() => {
  const name = props.user?.display_name || props.user?.name || '?'
  return name[0].toUpperCase()
})

const containerStyle = computed(() => {
  if (!scheme.value) return {}
  return {
    width: `${props.size}px`,
    height: `${props.size}px`,
    flexShrink: 0,
    background: scheme.value.bg,
    clipPath:
      'polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: `2px solid ${scheme.value.border}`,
    boxShadow: `0 0 8px ${scheme.value.border}60`,
    imageRendering: 'pixelated',
    cursor: 'default',
  }
})

const initialStyle = computed(() => ({
  fontFamily: "'m6x11plus', monospace",
  fontSize: `${Math.round(props.size * 0.32)}px`,
  color: '#fff',
  lineHeight: 1,
  userSelect: 'none',
  textShadow: '1px 1px 0 rgba(0,0,0,0.5)',
}))
</script>
