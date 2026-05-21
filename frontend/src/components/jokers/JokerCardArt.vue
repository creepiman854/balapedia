<!--
  Renderiza la "carta" SVG de un joker con datos del backend (JokerSchema).

  Estrategia visual:
   1. Si el joker trae `image_url`, lo respetamos y dibujamos sobre el
      marco pixelado (el backend va a poblar este campo cuando subamos
      los assets reales).
   2. Si no, generamos el visual a partir de:
        · `hue` derivado determinísticamente del nombre → tono base
        · `sym` derivado de la primera letra del nombre (mayúscula)
      Esto mantiene cada joker visualmente distinto y estable entre
      recargas (el mismo joker tendrá siempre el mismo hue) sin depender
      de campos cosméticos en BD.
   3. La rareza determina el color del borde y la banda inferior.

  Props:
    · joker     — objeto del backend (id, name, rarity UPPERCASE, image_url?)
    · width/height
    · isLocked  — gris + interrogante (cuando hay sesión y el usuario no lo
      tiene desbloqueado)
    · showLabel — banda inferior con nombre y rareza
-->
<template>
  <svg
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
    style="display: block; transition: all 0.2s"
  >
    <defs>
      <linearGradient :id="`${uid}bg`" x1="0" y1="0" x2="0.3" y2="1">
        <stop offset="0%" :stop-color="bg1" />
        <stop offset="100%" :stop-color="bg2" />
      </linearGradient>
      <linearGradient :id="`${uid}in`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="innerBg" />
        <stop offset="100%" :stop-color="bg1" />
      </linearGradient>
      <filter
        v-if="!isLocked"
        :id="`${uid}glow`"
        x="-20%"
        y="-20%"
        width="140%"
        height="140%"
      >
        <feGaussianBlur stdDeviation="2" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <clipPath :id="`${uid}clip`">
        <rect :x="8" :y="8" :width="width - 16" :height="artZoneH" />
      </clipPath>
    </defs>

    <!-- Fondo principal -->
    <rect :width="width" :height="height" :fill="`url(#${uid}bg)`" />
    <!-- Borde fino -->
    <rect
      :x="2"
      :y="2"
      :width="width - 4"
      :height="height - 4"
      fill="none"
      :stroke="accentColor"
      stroke-width="1.5"
      stroke-opacity="0.5"
    />
    <!-- Zona interior con gradiente -->
    <rect :x="8" :y="8" :width="width - 16" :height="artZoneH" :fill="`url(#${uid}in)`" />

    <!-- Imagen del backend si existe; si no, símbolo derivado -->
    <image
      v-if="!isLocked && joker.image_url"
      :href="joker.image_url"
      :x="8"
      :y="8"
      :width="width - 16"
      :height="artZoneH"
      :clip-path="`url(#${uid}clip)`"
      preserveAspectRatio="xMidYMid meet"
      style="image-rendering: pixelated"
    />
    <text
      v-else
      :x="width / 2"
      :y="symCenterY"
      text-anchor="middle"
      dominant-baseline="middle"
      font-size="44"
      :fill="symbolColor"
      :fill-opacity="isLocked ? '0.15' : '0.9'"
      font-family="'Segoe UI Symbol', 'Apple Color Emoji', serif"
      :filter="!isLocked ? `url(#${uid}glow)` : undefined"
    >{{ isLocked ? '?' : sym }}</text>

    <!-- Ornamentos esquina -->
    <text :x="5" :y="17" font-size="14" :fill="accentColor" fill-opacity="0.7" font-family="serif">◆</text>
    <text :x="width - 14" :y="17" font-size="14" :fill="accentColor" fill-opacity="0.7" font-family="serif">◆</text>

    <!-- Línea separadora (raras/legendarias con label) -->
    <rect
      v-if="!isLocked && (rarityKey === 'RARE' || rarityKey === 'LEGENDARY') && showLabel"
      :x="8"
      :y="height - 52"
      :width="width - 16"
      height="2"
      :fill="accentColor"
      fill-opacity="0.4"
    />

    <!-- Banda inferior con nombre + rareza -->
    <template v-if="showLabel">
      <rect :x="0" :y="height - 38" :width="width" height="38" fill="rgba(0,0,0,0.75)" />
      <rect :x="0" :y="height - 38" :width="width" height="2" :fill="accentColor" fill-opacity="0.8" />
      <text
        :x="width / 2"
        :y="height - 22"
        text-anchor="middle"
        dominant-baseline="middle"
        font-size="11"
        :fill="isLocked ? '#555' : '#fff'"
        font-family="'m6x11plus', monospace"
        letter-spacing="0.3"
      >{{ isLocked ? '???' : (joker.name || '').toUpperCase().substring(0, 13) }}</text>
      <text
        :x="width / 2"
        :y="height - 9"
        text-anchor="middle"
        dominant-baseline="middle"
        font-size="11"
        :fill="isLocked ? '#444' : accentColor"
        font-family="'m6x11plus', monospace"
      >{{ isLocked ? '?' : rarityInfo.label.toUpperCase() }}</text>
    </template>
  </svg>
</template>

<script setup>
import { computed } from 'vue'
import { getRarity } from '@/constants/rarity'

const props = defineProps({
  joker: { type: Object, required: true },
  width: { type: Number, default: 130 },
  height: { type: Number, default: 180 },
  isLocked: { type: Boolean, default: false },
  showLabel: { type: Boolean, default: false },
})

const rarityKey = computed(() => String(props.joker.rarity || '').toUpperCase())
const rarityInfo = computed(() => getRarity(rarityKey.value))

// SVG ids únicos por instancia, si no se solapan los gradientes al
// montar varias cartas en el grid.
const uid = computed(() => `jc${props.joker.id}`)

/**
 * Genera un tono HSL determinístico a partir del nombre. Mismo joker →
 * mismo color en cada render, así no parpadea al recargar.
 */
function nameHue(name) {
  if (!name) return 200
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) % 360
  return h
}

const hue = computed(() => nameHue(props.joker.name))

const sym = computed(() => {
  // Primera letra mayúscula del nombre como símbolo. Cuando el backend
  // tenga `image_url` poblado este fallback ni se renderiza.
  return (props.joker.name || '?').trim()[0]?.toUpperCase() || '?'
})

const accentColor = computed(() =>
  props.isLocked ? '#444' : rarityInfo.value.color,
)
const symbolColor = computed(() =>
  props.isLocked ? '#333' : `hsl(${hue.value}, 80%, 70%)`,
)
const bg1 = computed(() =>
  props.isLocked ? '#111' : `hsl(${hue.value}, 50%, 7%)`,
)
const bg2 = computed(() =>
  props.isLocked ? '#1a1a1a' : `hsl(${hue.value}, 40%, 14%)`,
)
const innerBg = computed(() =>
  props.isLocked ? '#1a1a1a' : `hsl(${hue.value}, 35%, 10%)`,
)
const artZoneH = computed(() => (props.showLabel ? props.height - 48 : props.height - 16))
const symCenterY = computed(() => 8 + artZoneH.value / 2)
</script>
