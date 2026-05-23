<!--
  Tooltip flotante sobre una carta. Recibe:
    · joker (shape del backend: name, description, rarity UPPERCASE,
      unlock_condition, unlock_factor)
    · isLocked
    · cardCenterX, cardTop (en coords de viewport — fixed)

  Para jokers bloqueados muestra `unlock_condition` o
  `unlock_factor.description`, lo que esté disponible.
  Para los desbloqueados muestra `description` con los fragmentos
  numéricos coloreados igual que en el juego original.
-->
<template>
  <div :style="posStyle">
    <div v-if="isLocked" :style="lockedBoxStyle">
      <div :style="lockedHeaderStyle">
        <span :style="lockedHeaderTextStyle">Por descubrir</span>
      </div>
      <div :style="lockedBodyStyle">
        <p :style="lockedBodyTextStyle">{{ unlockText }}</p>
      </div>
    </div>

    <div v-else :style="boxStyle">
      <div :style="headerStyle">
        <span :style="headerTextStyle">{{ joker.name }}</span>
      </div>
      <div :style="bodyStyle">
        <p :style="bodyTextStyle">
          <template v-for="(part, i) in coloredParts" :key="i">
            <strong v-if="part.color !== '#2a2a2a'" :style="{ color: part.color, fontWeight: 700 }">{{
              part.text
            }}</strong>
            <span v-else>{{ part.text }}</span>
          </template>
        </p>
      </div>
      <div :style="footerStyle">
        <RarityBadge :rarity="joker.rarity" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getRarity } from '@/constants/rarity'
import RarityBadge from '@/components/common/RarityBadge.vue'

const props = defineProps({
  joker: { type: Object, required: true },
  isLocked: { type: Boolean, default: false },
  cardCenterX: { type: Number, required: true },
  cardTop: { type: Number, required: true },
})

const TOOLTIP_W = 230
const TEAL = {
  shadow: '#1E2E32',
  darkest: '#1A2A2E',
  dark: '#253C40',
  mid: '#3A5055',
  text1: '#E8F2F4',
  text2: '#A8C4C8',
}

const PIXEL_CLIP =
  'polygon(0px calc(100% - 12px), 3px calc(100% - 12px), 3px calc(100% - 6px), 6px calc(100% - 6px), 6px calc(100% - 3px), 12px calc(100% - 3px), 12px 100%, calc(100% - 12px) 100%, calc(100% - 12px) calc(100% - 3px), calc(100% - 6px) calc(100% - 3px), calc(100% - 6px) calc(100% - 6px), calc(100% - 3px) calc(100% - 6px), calc(100% - 3px) calc(100% - 12px), 100% calc(100% - 12px), 100% 12px, calc(100% - 3px) 12px, calc(100% - 3px) 6px, calc(100% - 6px) 6px, calc(100% - 6px) 3px, calc(100% - 12px) 3px, calc(100% - 12px) 0px, 12px 0px, 12px 3px, 6px 3px, 6px 6px, 3px 6px, 3px 12px, 0px 12px)'

const PIXEL_CLIP_SM =
  'polygon(0px calc(100% - 8px), 2px calc(100% - 8px), 2px calc(100% - 4px), 4px calc(100% - 4px), 4px calc(100% - 2px), 8px calc(100% - 2px), 8px 100%, calc(100% - 8px) 100%, calc(100% - 8px) calc(100% - 2px), calc(100% - 4px) calc(100% - 2px), calc(100% - 4px) calc(100% - 4px), calc(100% - 2px) calc(100% - 4px), calc(100% - 2px) calc(100% - 8px), 100% calc(100% - 8px), 100% 8px, calc(100% - 2px) 8px, calc(100% - 2px) 4px, calc(100% - 4px) 4px, calc(100% - 4px) 2px, calc(100% - 8px) 2px, calc(100% - 8px) 0px, 8px 0px, 8px 2px, 4px 2px, 4px 4px, 2px 4px, 2px 8px, 0px 8px)'

const rarity = computed(() => getRarity(props.joker.rarity))

const unlockText = computed(
  () =>
    props.joker.unlock_condition ||
    props.joker.unlock_factor?.description ||
    'Compra o usa esta carta en una partida sin códigos para saber lo que hace.',
)

const description = computed(() => props.joker.description || '—')

const posStyle = computed(() => {
  const left = Math.max(
    8,
    Math.min(props.cardCenterX - TOOLTIP_W / 2, window.innerWidth - TOOLTIP_W - 8),
  )
  const bottom = window.innerHeight - props.cardTop + 10
  return {
    position: 'fixed',
    bottom: `${bottom}px`,
    left: `${left}px`,
    zIndex: 9000,
    width: `${TOOLTIP_W}px`,
    pointerEvents: 'none',
    animation: 'tooltipFadeIn 0.12s ease',
  }
})

// ── Bloqueado ──
const lockedBoxStyle = computed(() => ({
  background: TEAL.dark,
  clipPath: PIXEL_CLIP,
  filter: `drop-shadow(0 6px 20px ${TEAL.shadow})`,
  overflow: 'hidden',
}))
const lockedHeaderStyle = {
  background: TEAL.mid,
  padding: '10px 12px',
  textAlign: 'center',
}
const lockedHeaderTextStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: '16px',
  color: TEAL.text2,
  letterSpacing: '0.5px',
}
const lockedBodyStyle = {
  background: '#c8c8c8',
  margin: '6px',
  padding: '10px',
  clipPath: PIXEL_CLIP_SM,
}
const lockedBodyTextStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: '16px',
  color: '#2a2a2a',
  margin: 0,
  textAlign: 'center',
  lineHeight: 1.5,
}

// ── Desbloqueado ──
const boxStyle = computed(() => ({
  background: TEAL.darkest,
  clipPath: PIXEL_CLIP,
  filter: `drop-shadow(0 6px 20px rgba(0,0,0,0.9)) drop-shadow(0 0 12px ${rarity.value.glow})`,
  overflow: 'hidden',
}))
const headerStyle = computed(() => ({
  background: TEAL.mid,
  padding: '10px 14px',
  textAlign: 'center',
  borderBottom: `2px solid ${rarity.value.color}30`,
}))
const headerTextStyle = computed(() => ({
  fontFamily: "'m6x11plus', monospace",
  fontSize: '16px',
  color: '#fff',
  letterSpacing: '0.5px',
  textShadow: `0 0 10px ${rarity.value.color}`,
}))
const bodyStyle = {
  background: '#e8e4f0',
  margin: '6px',
  padding: '10px 12px',
  clipPath: PIXEL_CLIP_SM,
}
const bodyTextStyle = {
  fontFamily: "'m6x11plus', monospace",
  fontSize: '16px',
  color: '#1a1a1a',
  margin: 0,
  textAlign: 'center',
  lineHeight: 1.6,
}
const footerStyle = {
  padding: '6px 10px 10px',
  display: 'flex',
  justifyContent: 'center',
}

/**
 * Coloriza fragmentos como `+N Mult`, `XN Mult`, `+N Fichas`, `$N` y los
 * iconos de palo en la descripción del joker, igual que el tooltip del
 * juego original.
 */
const coloredParts = computed(() => {
  const parts = description.value.split(
    /(\+\d+\s*Mult|\+\d+\s*Fichas|X[\d.]+\s*Mult|\$\d+|♦|♥|♠|♣|\d+\/\d+)/g,
  )
  return parts.map((part) => {
    let color = '#2a2a2a'
    if (/\+\d+\s*Mult|X[\d.]+\s*Mult/.test(part)) color = '#c03030'
    else if (/\+\d+\s*Fichas/.test(part)) color = '#2060c0'
    else if (/\$\d+/.test(part)) color = '#b07800'
    else if (/♦/.test(part)) color = '#c07800'
    else if (/♥/.test(part)) color = '#c02020'
    else if (/♠/.test(part)) color = '#6030b0'
    else if (/♣/.test(part)) color = '#1080a0'
    return { text: part, color }
  })
})
</script>
