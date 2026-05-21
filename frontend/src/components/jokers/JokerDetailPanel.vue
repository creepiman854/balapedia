<!--
  Panel derecho con el detalle del joker seleccionado.

  Si `joker` es null, placeholder. El shape del joker viene del backend
  (JokerSchema), no del diseño mock:
    · description       (texto largo del efecto)
    · effect_type       (categoría: "Mult Aditivo", "Economía"...)
    · activation        (trigger: "Al Puntuar Carta", "Pasivo"...)
    · buy_price / sell_price
    · is_copyable / is_perishable / is_eternal
    · unlock_condition o unlock_factor.description

  Y si está autenticado, también:
    · unlocked_for_me   (bool)
    · highest_stake_order (1..8 — sticker dorado = 8)
-->
<template>
  <div v-if="!joker" class="empty">
    <div class="empty__icon">?</div>
    <p class="empty__text">Selecciona un<br />Comodín para<br />ver los detalles</p>
  </div>

  <div v-else class="detail">
    <!-- Arte de carta grande -->
    <div class="detail__art" :style="artBgStyle">
      <div :style="{ filter: `drop-shadow(0 0 18px ${rarity.glow})` }">
        <JokerCardArt :joker="joker" :width="160" :height="224" :is-locked="isLocked" :show-label="false" />
      </div>
    </div>

    <div class="detail__body">
      <!-- EFECTO -->
      <section class="section">
        <header class="section__head" :style="{ borderLeftColor: rarity.color }">
          <span style="font-size: 15px">⚡</span>
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
            {{ isLocked ? '???' : (joker.description || '—') }}
          </div>
        </div>
      </section>

      <!-- RAREZA -->
      <section class="section">
        <header class="section__head" :style="{ borderLeftColor: rarity.color }">
          <span style="font-size: 15px">◆</span>
          <span :style="{ color: rarity.color }">RAREZA</span>
        </header>
        <div class="section__body" style="display: flex; justify-content: center; padding: 4px 0">
          <div :style="{ filter: `drop-shadow(0 0 8px ${rarity.glow})` }">
            <RarityBadge :rarity="joker.rarity" />
          </div>
        </div>
      </section>

      <!-- DESBLOQUEO -->
      <section v-if="unlockText" class="section">
        <header class="section__head" style="border-left-color: #708387">
          <span style="font-size: 15px">🔓</span>
          <span>DESBLOQUEO</span>
        </header>
        <div class="section__body section__body--unlock">
          {{ unlockText }}
        </div>
      </section>

      <!-- ESTADO DE USUARIO (sólo si está autenticado y backend devuelve overlay) -->
      <section v-if="hasOverlay" class="section">
        <header class="section__head" style="border-left-color: #22c55e">
          <span style="font-size: 15px">{{ joker.unlocked_for_me ? '✓' : '🔒' }}</span>
          <span style="color: #22c55e">MI PROGRESO</span>
        </header>
        <div class="section__body progress-box">
          <div v-if="joker.unlocked_for_me" class="progress-row">
            <span>Desbloqueado</span>
            <span class="progress-row__val">{{ formatDate(joker.unlocked_at) }}</span>
          </div>
          <div v-else class="progress-row">
            <span>Aún no desbloqueado</span>
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
          <span style="font-size: 15px">📊</span>
          <span style="color: #c09020">ESTADÍSTICAS</span>
        </header>
        <div class="section__body stats">
          <div class="stats__row">
            <div class="stat stat--buy">
              <div class="stat__label">COMPRA</div>
              <div class="stat__value">{{ joker.buy_price != null ? `$${joker.buy_price}` : '—' }}</div>
            </div>
            <div class="stat stat--sell">
              <div class="stat__label">VENTA</div>
              <div class="stat__value">{{ joker.sell_price != null ? `$${joker.sell_price}` : '—' }}</div>
            </div>
          </div>
          <div v-if="joker.effect_type || joker.activation" class="stats__row">
            <div class="stat stat--info">
              <div class="stat__label">TIPO</div>
              <div class="stat__value stat__value--sm">{{ joker.effect_type || '—' }}</div>
            </div>
            <div class="stat stat--info">
              <div class="stat__label">ACTIV.</div>
              <div class="stat__value stat__value--sm">{{ joker.activation || '—' }}</div>
            </div>
          </div>
        </div>
      </section>

      <!-- COMPATIBILIDAD -->
      <section v-if="joker.is_copyable || joker.is_perishable || joker.is_eternal" class="section">
        <header class="section__head" style="border-left-color: #708387">
          <span style="font-size: 15px">⚙</span>
          <span>COMPATIBILIDAD</span>
        </header>
        <div class="section__body compat">
          <div v-if="joker.is_copyable" class="compat__tile" style="--c: #20c050">
            <div style="font-size: 18px">⎘</div>
            <div class="compat__label">Copiable</div>
          </div>
          <div v-if="joker.is_perishable" class="compat__tile" style="--c: #e08020">
            <div style="font-size: 18px">⏳</div>
            <div class="compat__label">Perece</div>
          </div>
          <div v-if="joker.is_eternal" class="compat__tile" style="--c: #6080e0">
            <div style="font-size: 18px">∞</div>
            <div class="compat__label">Eterno</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getRarity } from '@/constants/rarity'
import JokerCardArt from './JokerCardArt.vue'
import RarityBadge from '@/components/common/RarityBadge.vue'

const props = defineProps({
  joker: { type: Object, default: null },
  isLocked: { type: Boolean, default: false },
})

const rarity = computed(() => (props.joker ? getRarity(props.joker.rarity) : {}))

const artBgStyle = computed(() => ({
  background: `linear-gradient(180deg, ${rarity.value.dark || '#000'} 0%, #1A2A2E 100%)`,
}))

const unlockText = computed(() => {
  if (!props.joker) return ''
  return props.joker.unlock_condition || props.joker.unlock_factor?.description || ''
})

// `unlocked_for_me` solo aparece cuando el endpoint es /api/me/jokers
// (usuario autenticado). Si el campo está literalmente ausente del item,
// significa que estamos sirviendo desde /api/jokers (público) → no
// mostramos la sección de progreso.
const hasOverlay = computed(
  () => props.joker && Object.prototype.hasOwnProperty.call(props.joker, 'unlocked_for_me'),
)

const stakeColor = computed(() => {
  // Sticker dorado (stake 8) = oro; resto = verde suave.
  if (props.joker?.highest_stake_order === 8) return '#f0b030'
  return '#22c55e'
})

function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString()
  } catch {
    return iso
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
    font-size: 48px;
    font-family: 'm6x11plus', monospace;
    color: $panel-light;
  }
  &__text {
    font-family: 'm6x11plus', monospace;
    font-size: 13px;
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

  &__art {
    display: flex;
    justify-content: center;
    padding: 16px 0 12px;
  }

  &__body {
    overflow-y: auto;
    flex: 1;
    padding: 0 10px 16px;
  }
}

.section {
  margin-bottom: 10px;

  &__head {
    background: $panel-mid;
    padding: 7px 12px;
    border-left: 4px solid $panel-light;
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'm6x11plus', monospace;
    font-size: 11px;
    color: $text-1;
    letter-spacing: 0.5px;
  }

  &__body {
    padding: 8px 10px;
  }

  &__body--unlock {
    text-align: center;
    font-family: 'm6x11plus', monospace;
    font-size: 13px;
    color: $text-2;
    line-height: 1.6;
  }
}

.effect-box {
  padding: 10px 12px;
  text-align: center;
  font-family: 'm6x11plus', monospace;
  font-size: 13px;
  line-height: 1.5;
  font-weight: 700;
  @include pixel-clip-sm;
}

.progress-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 4px;
}
.progress-row {
  display: flex;
  justify-content: space-between;
  font-family: 'm6x11plus', monospace;
  font-size: 12px;
  color: $text-2;

  &__val {
    color: $text-1;
  }
}

.stats {
  display: flex;
  flex-direction: column;
  gap: 6px;

  &__row {
    display: flex;
    gap: 6px;
  }
}

.stat {
  flex: 1;
  text-align: center;
  padding: 8px 0;
  font-family: 'm6x11plus', monospace;
  @include pixel-clip-sm;

  &__label {
    font-size: 11px;
  }

  &__value {
    font-size: 20px;
    font-weight: 700;
    &--sm {
      font-size: 12px;
      color: $text-1;
      line-height: 1.4;
    }
  }

  &--buy {
    background: #c0902018;
    border: 1px solid #c0902045;
    color: #c09020;
    .stat__value { color: #f0b030; }
  }
  &--sell {
    background: #40802018;
    border: 1px solid #40802045;
    color: #40a030;
    .stat__value { color: #60c050; }
  }
  &--info {
    background: $panel-dark;
    padding: 8px 10px;
    text-align: left;
    .stat__label { color: $panel-light; margin-bottom: 3px; }
  }
}

.compat {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;

  &__tile {
    flex: 1;
    min-width: 60px;
    background: color-mix(in srgb, var(--c) 9%, transparent);
    border: 1px solid color-mix(in srgb, var(--c) 27%, transparent);
    padding: 8px 6px;
    text-align: center;
    @include pixel-clip-sm;
  }

  &__label {
    font-family: 'm6x11plus', monospace;
    font-size: 11px;
    margin-top: 4px;
    color: var(--c);
  }
}
</style>
