<!--
  Panel derecho con el detalle del joker seleccionado.

  Pase 5:
   · Firefox-compat: reemplazado `color-mix(in srgb, ...)` (que falla
     en versiones antiguas / equivale a `transparent` por error) por
     rgba() hardcoded calculado a mano por cada tile de COMPATIBILIDAD.
   · El resto del comportamiento se mantiene.
-->
<template>
  <div v-if="!joker" class="empty">
    <div class="empty__icon">?</div>
    <p class="empty__text">Selecciona un<br />Comodín para<br />ver los detalles</p>
  </div>

  <div v-else class="detail">
    <!-- Arte de carta — suelto, con tilt. -->
    <div class="detail__art-wrap">
      <div
        v-tilt="{ max: 10, scale: 1.04, speed: 400 }"
        class="detail__art"
        :style="{ filter: `drop-shadow(0 0 22px ${rarity.glow}) drop-shadow(0 8px 16px rgba(0,0,0,0.65))` }"
      >
        <JokerCardArt :joker="joker" :is-locked="isLocked" />
      </div>
    </div>

    <div class="detail__body">
      <!-- Desbloqueo manual -->
      <button
        v-if="isLocked"
        class="manual-unlock"
        :disabled="busy"
        @click="onManualUnlock"
      >
        {{ busy ? 'Desbloqueando...' : 'Marcar como desbloqueado' }}
      </button>

      <!-- EFECTO -->
      <section class="section">
        <header class="section__head" :style="{ borderLeftColor: rarity.color }">
          <span class="section__icon">⚡</span>
          <span :style="{ color: rarity.color }">EFECTO</span>
        </header>
        <div class="section__body">
          <div
            class="effect-box"
            :style="{
              background: `${rarity.color}15`,
              border: `1px solid ${rarity.color}40`,
              color: isLocked ? '#4D6870' : rarity.color,
            }"
          >
            {{ isLocked ? '???' : safe(joker.description) }}
          </div>
        </div>
      </section>

      <!-- RAREZA -->
      <section class="section">
        <header class="section__head" :style="{ borderLeftColor: rarity.color }">
          <span class="section__icon">◆</span>
          <span :style="{ color: rarity.color }">RAREZA</span>
        </header>
        <div class="section__body section__body--center">
          <div :style="{ filter: `drop-shadow(0 0 8px ${rarity.glow})` }">
            <RarityBadge :rarity="joker.rarity" />
          </div>
        </div>
      </section>

      <!-- DESBLOQUEO -->
      <section v-if="unlockText" class="section">
        <header class="section__head" style="border-left-color: #708387">
          <span class="section__icon">🔓</span>
          <span>DESBLOQUEO</span>
        </header>
        <div class="section__body section__body--unlock">
          {{ unlockText }}
        </div>
      </section>

      <!-- MI PROGRESO -->
      <section v-if="hasOverlay" class="section">
        <header class="section__head" style="border-left-color: #22c55e">
          <span class="section__icon">{{ joker.unlocked_for_me ? '✓' : '🔒' }}</span>
          <span style="color: #22c55e">MI PROGRESO</span>
        </header>
        <div class="section__body progress-box">
          <div class="progress-row">
            <span>Estado</span>
            <span class="progress-row__val">
              {{ joker.unlocked_for_me ? 'Desbloqueado' : 'Bloqueado' }}
            </span>
          </div>
          <div v-if="joker.unlocked_for_me && unlockedAtText" class="progress-row">
            <span>Desde</span>
            <span class="progress-row__val">{{ unlockedAtText }}</span>
          </div>
          <div v-if="joker.highest_stake_order" class="progress-row">
            <span>Stake máximo</span>
            <span class="progress-row__val" :style="{ color: stakeColor }">
              {{ joker.highest_stake_order === 8 ? '★ ORO' : `Stake ${joker.highest_stake_order}` }}
            </span>
          </div>
        </div>
      </section>

      <!-- ESTADÍSTICAS -->
      <section class="section">
        <header class="section__head" style="border-left-color: #c09020">
          <span class="section__icon">📊</span>
          <span style="color: #c09020">ESTADÍSTICAS</span>
        </header>
        <div class="section__body stats">
          <div class="stats__row">
            <div class="stat stat--buy">
              <div class="stat__label">COMPRA</div>
              <div class="stat__value">{{ formatPrice(joker.buy_price) }}</div>
            </div>
            <div class="stat stat--sell">
              <div class="stat__label">VENTA</div>
              <div class="stat__value">{{ formatPrice(joker.sell_price) }}</div>
            </div>
          </div>
          <div v-if="hasEffectMeta" class="stats__row">
            <div v-if="joker.effect_type" class="stat stat--info">
              <div class="stat__label">TIPO</div>
              <div class="stat__value stat__value--sm">{{ joker.effect_type }}</div>
            </div>
            <div v-if="joker.activation" class="stat stat--info">
              <div class="stat__label">ACTIV.</div>
              <div class="stat__value stat__value--sm">{{ joker.activation }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- COMPATIBILIDAD -->
      <section v-if="hasCompat" class="section">
        <header class="section__head" style="border-left-color: #708387">
          <span class="section__icon">⚙</span>
          <span>COMPATIBILIDAD</span>
        </header>
        <div class="section__body compat">
          <div v-if="joker.is_copyable" class="compat__tile compat__tile--copy">
            <div class="compat__symbol">⎘</div>
            <div class="compat__label">Copiable</div>
          </div>
          <div v-if="joker.is_perishable" class="compat__tile compat__tile--perish">
            <div class="compat__symbol">⏳</div>
            <div class="compat__label">Perece</div>
          </div>
          <div v-if="joker.is_eternal" class="compat__tile compat__tile--eternal">
            <div class="compat__symbol">∞</div>
            <div class="compat__label">Eterno</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { getRarity } from '@/constants/rarity'
import JokerCardArt from './JokerCardArt.vue'
import RarityBadge from '@/components/common/RarityBadge.vue'

const props = defineProps({
  joker: { type: Object, default: null },
  isLocked: { type: Boolean, default: false },
})

const emit = defineEmits(['manual-unlock'])

const busy = ref(false)

const rarity = computed(() => (props.joker ? getRarity(props.joker.rarity) : {}))

const hasOverlay = computed(
  () => props.joker && Object.prototype.hasOwnProperty.call(props.joker, 'unlocked_for_me'),
)

const hasEffectMeta = computed(
  () => props.joker && (props.joker.effect_type || props.joker.activation),
)

const hasCompat = computed(
  () =>
    props.joker &&
    (props.joker.is_copyable || props.joker.is_perishable || props.joker.is_eternal),
)

const unlockText = computed(() => {
  if (!props.joker) return ''
  return props.joker.unlock_condition || props.joker.unlock_factor?.description || ''
})

const stakeColor = computed(() => {
  if (props.joker?.highest_stake_order === 8) return '#f0b030'
  return '#22c55e'
})

const unlockedAtText = computed(() => {
  if (!props.joker?.unlocked_at) return ''
  try {
    return new Date(props.joker.unlocked_at).toLocaleDateString()
  } catch {
    return ''
  }
})

function safe(value, fallback = '—') {
  if (value == null) return fallback
  if (typeof value === 'string' && !value.trim()) return fallback
  return value
}

function formatPrice(v) {
  if (!Number.isFinite(Number(v))) return '—'
  return `$${Number(v)}`
}

async function onManualUnlock() {
  if (busy.value || !props.joker) return
  busy.value = true
  try {
    emit('manual-unlock', props.joker)
  } finally {
    setTimeout(() => (busy.value = false), 800)
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  opacity: 0.4;

  &__icon {
    font-size: 56px;
    font-family: 'm6x11plus', monospace;
    color: $panel-light;
  }
  &__text {
    font-family: 'm6x11plus', monospace;
    font-size: 14px;
    color: $panel-light;
    text-align: center;
    line-height: 1.8;
  }
}

.detail {
  background: $panel-darkest;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.detail__art-wrap {
  display: flex;
  justify-content: center;
  padding: 18px 30px 14px;
  flex-shrink: 0;
}

/*
 * Card reducida (era 75% / 220px) — el panel completo cabe sin
 * necesidad de scroll en pantallas razonables.
 */
.detail__art {
  width: 58%;
  max-width: 170px;
  transform-style: preserve-3d;
}

.detail__body {
  overflow-y: auto;
  flex: 1;
  padding: 0 14px 18px;
  scrollbar-width: thin;
  scrollbar-color: $panel-mid transparent;
}

.manual-unlock {
  width: 100%;
  margin-bottom: 12px;
  background: #1a4030;
  border: 1px solid #22c55e;
  color: #22c55e;
  font-family: 'm6x11plus', monospace;
  font-size: 13px;
  letter-spacing: 0.5px;
  padding: 10px 12px;
  cursor: pointer;
  transition: filter 0.15s, transform 0.1s;
  @include pixel-clip-sm;

  &:hover:not(:disabled) {
    filter: brightness(1.2);
  }
  &:active:not(:disabled) {
    transform: scale(0.97);
  }
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.section {
  margin-bottom: 12px;

  &__head {
    background: $panel-mid;
    padding: 8px 14px;
    border-left: 4px solid $panel-light;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'm6x11plus', monospace;
    font-size: 12px;
    color: $text-1;
    letter-spacing: 0.5px;
  }
  &__icon {
    font-size: 15px;
  }

  &__body {
    padding: 10px 12px;
  }

  &__body--center {
    display: flex;
    justify-content: center;
    padding: 8px 12px;
  }

  &__body--unlock {
    text-align: center;
    font-family: 'm6x11plus', monospace;
    font-size: 14px;
    color: $text-2;
    line-height: 1.6;
  }
}

.effect-box {
  padding: 12px 14px;
  text-align: center;
  font-family: 'm6x11plus', monospace;
  font-size: 14px;
  line-height: 1.55;
  font-weight: 700;
  @include pixel-clip-sm;
}

.progress-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px;
}
.progress-row {
  display: flex;
  justify-content: space-between;
  font-family: 'm6x11plus', monospace;
  font-size: 13px;
  color: $text-2;

  &__val {
    color: $text-1;
  }
}

.stats {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__row {
    display: flex;
    gap: 8px;
  }
}

.stat {
  flex: 1;
  text-align: center;
  padding: 10px 4px;
  font-family: 'm6x11plus', monospace;
  @include pixel-clip-sm;

  &__label {
    font-size: 12px;
  }

  &__value {
    font-size: 22px;
    font-weight: 700;

    &--sm {
      font-size: 13px;
      color: $text-1;
      line-height: 1.4;
      font-weight: normal;
    }
  }

  &--buy {
    background: rgba(192, 144, 32, 0.094);
    border: 1px solid rgba(192, 144, 32, 0.27);
    color: #c09020;
    .stat__value { color: #f0b030; }
  }
  &--sell {
    background: rgba(64, 128, 32, 0.094);
    border: 1px solid rgba(64, 128, 32, 0.27);
    color: #40a030;
    .stat__value { color: #60c050; }
  }
  &--info {
    background: $panel-dark;
    padding: 10px 12px;
    text-align: left;
    .stat__label { color: $panel-light; margin-bottom: 4px; }
  }
}

/*
 * COMPATIBILIDAD — fondos y bordes precalculados a rgba() en vez de
 * color-mix(). Firefox antiguo no parsea color-mix() correctamente y
 * dejaba los tiles transparentes.
 */
.compat {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 4px;

  &__tile {
    flex: 1;
    min-width: 72px;
    padding: 10px 6px;
    text-align: center;
    border: 1px solid;
    @include pixel-clip-sm;
  }

  &__tile--copy {
    background: rgba(32, 192, 80, 0.09);
    border-color: rgba(32, 192, 80, 0.27);
    .compat__label { color: #20c050; }
  }
  &__tile--perish {
    background: rgba(224, 128, 32, 0.09);
    border-color: rgba(224, 128, 32, 0.27);
    .compat__label { color: #e08020; }
  }
  &__tile--eternal {
    background: rgba(96, 128, 224, 0.09);
    border-color: rgba(96, 128, 224, 0.27);
    .compat__label { color: #6080e0; }
  }

  &__symbol {
    font-size: 22px;
    line-height: 1;
  }

  &__label {
    font-family: 'm6x11plus', monospace;
    font-size: 12px;
    margin-top: 6px;
  }
}
</style>
