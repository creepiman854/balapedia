<!--
  Panel derecho con el detalle del item seleccionado.

  Genérico para joker / consumible / (otros en futuro). Las secciones
  que no aplican a un tipo concreto se ocultan con v-if:
    - RAREZA / TIPO → siempre una (rareza si es joker; tipo si es
      consumible), nunca ambas.
    - EFECTO → siempre (la descripción).
    - DESBLOQUEO → si hay unlock_condition o unlock_factor.
    - (MI PROGRESO se eliminó: el estado visual de la carta — imagen
      vs dorso — ya comunica el unlock state al usuario.)
    - ESTADÍSTICAS → buy/sell siempre; effect_type/activation solo si
      el shape los trae (jokers).
    - COMPATIBILIDAD → solo si alguno de is_copyable/perishable/eternal
      es true (jokers).
-->
<template>
  <div v-if="!item" class="empty">
    <div class="empty__icon">?</div>
    <p class="empty__text">Selecciona una<br />carta para ver<br />los detalles</p>
  </div>

  <div v-else class="detail">
    <!-- Arte -->
    <div class="detail__art-wrap">
      <div
        v-tilt="{ max: 10, scale: 1.04, speed: 400 }"
        class="detail__art"
      >
        <ItemCardArt
          :item="item"
          :is-locked="isLocked"
          :is-selected="false"
          :accent="accent"
        />
      </div>
    </div>

    <div class="detail__body">
      <!-- Desbloqueo manual (solo si está locked Y el padre admite el evento) -->
      <button
        v-if="isLocked && canUnlock"
        class="manual-unlock"
        :disabled="busy"
        @click="onManualUnlock"
      >
        {{ busy ? 'Desbloqueando...' : 'Marcar como desbloqueado' }}
      </button>

      <!-- EFECTO -->
      <section class="section">
        <header class="section__head" :style="{ borderLeftColor: accent.color }">
          <span class="section__icon">⚡</span>
          <span :style="{ color: accent.color }">EFECTO</span>
        </header>
        <div class="section__body">
          <div
            class="effect-box"
            :style="{
              background: `${accent.color}15`,
              border: `1px solid ${accent.color}40`,
              color: isLocked ? '#4D6870' : accent.color,
            }"
          >
            {{ displayEffect }}
          </div>
        </div>
      </section>

      <!-- RAREZA / TIPO -->
      <section v-if="badgeLabel" class="section">
        <header class="section__head" :style="{ borderLeftColor: accent.color }">
          <span class="section__icon">◆</span>
          <span :style="{ color: accent.color }">{{ item.rarity ? 'RAREZA' : 'TIPO' }}</span>
        </header>
        <div class="section__body section__body--center">
          <div :style="{ filter: `drop-shadow(0 0 8px ${accent.glow})` }">
            <AccentBadge :label="badgeLabel" :color="accent.color" :glow="accent.glow" />
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

      <!--
        Sección "MI PROGRESO" eliminada: el usuario ya sabe si una
        carta está desbloqueada o no por su propia imagen — si se ve,
        está desbloqueada; si aparece el dorso "?", está bloqueada.
        El bloque sobraba.
      -->

      <!-- MEJORA A (vouchers base con next_voucher_id) -->
      <section v-if="item._nextVoucher" class="section">
        <header class="section__head" style="border-left-color: #3b82f6">
          <span class="section__icon">⬆</span>
          <span style="color: #3b82f6">MEJORA A</span>
        </header>
        <div class="section__body upgrade-box">
          <img
            v-if="item._nextVoucher.image_url"
            :src="item._nextVoucher.image_url"
            :alt="item._nextVoucher.name"
            class="upgrade-box__thumb"
            draggable="false"
          />
          <div v-else class="upgrade-box__thumb upgrade-box__thumb--missing">?</div>
          <span class="upgrade-box__name">{{ item._nextVoucher.name }}</span>
        </div>
      </section>

      <!-- ESTADÍSTICAS -->
      <section v-if="hasStats" class="section">
        <header class="section__head" style="border-left-color: #c09020">
          <span class="section__icon">📊</span>
          <span style="color: #c09020">ESTADÍSTICAS</span>
        </header>
        <div class="section__body stats">
          <div class="stats__row">
            <div class="stat stat--buy">
              <div class="stat__label">COMPRA</div>
              <div class="stat__value">{{ formatPrice(item.buy_price) }}</div>
            </div>
            <div class="stat stat--sell">
              <div class="stat__label">VENTA</div>
              <div class="stat__value">{{ formatPrice(item.sell_price) }}</div>
            </div>
          </div>
          <div v-if="hasEffectMeta" class="stats__row">
            <div v-if="item.effect_type" class="stat stat--info">
              <div class="stat__label">TIPO</div>
              <div class="stat__value stat__value--sm">{{ item.effect_type }}</div>
            </div>
            <div v-if="item.activation" class="stat stat--info">
              <div class="stat__label">ACTIV.</div>
              <div class="stat__value stat__value--sm">{{ item.activation }}</div>
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
          <div v-if="item.is_copyable" class="compat__tile compat__tile--copy">
            <div class="compat__symbol">⎘</div>
            <div class="compat__label">Copiable</div>
          </div>
          <div v-if="item.is_perishable" class="compat__tile compat__tile--perish">
            <div class="compat__symbol">⏳</div>
            <div class="compat__label">Perece</div>
          </div>
          <div v-if="item.is_eternal" class="compat__tile compat__tile--eternal">
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
import { getItemAccent, getItemBadgeLabel, getItemEffectText } from '@/constants/items'
import ItemCardArt from './ItemCardArt.vue'
import AccentBadge from '@/components/common/AccentBadge.vue'

const props = defineProps({
  item: { type: Object, default: null },
  isLocked: { type: Boolean, default: false },
  /**
   * Si true, muestra el botón de "desbloqueo manual" cuando isLocked.
   * Para jokers va a true; para consumibles, false mientras no exista
   * el endpoint correspondiente.
   */
  canUnlock: { type: Boolean, default: false },
})

const emit = defineEmits(['manual-unlock'])

const busy = ref(false)

const accent = computed(() => (props.item ? getItemAccent(props.item) : {}))
const badgeLabel = computed(() => getItemBadgeLabel(props.item))
// `description` (jokers, decks, vouchers, packs) o `effect`
// (card modifiers). El helper centraliza la resolución.
/**
 * Texto a mostrar en la sección EFECTO.
 *
 * Antes hacíamos `safe(effectText)` en la plantilla pero pasar un
 * ref (`effectText`) como argumento de función dentro de una
 * expresión `{{ }}` puede no des-envolverse automáticamente en
 * todos los escenarios (Vue 3 lo hace en accesos top-level pero
 * la garantía decae cuando se anida en otras expresiones).
 *
 * Lo movemos a un único computed que devuelve directamente la
 * cadena final ('???' si locked, '—' si vacío, el efecto en
 * cualquier otro caso). El template solo hace `{{ displayEffect }}`,
 * top-level → unwrap garantizado.
 */
const displayEffect = computed(() => {
  if (props.isLocked) return '???'
  const text = getItemEffectText(props.item)
  if (!text || (typeof text === 'string' && !text.trim())) return '—'
  return text
})

const hasStats = computed(
  () =>
    props.item &&
    (props.item.buy_price != null ||
      props.item.sell_price != null ||
      props.item.effect_type ||
      props.item.activation),
)

const hasEffectMeta = computed(
  () => props.item && (props.item.effect_type || props.item.activation),
)

const hasCompat = computed(
  () =>
    props.item &&
    (props.item.is_copyable || props.item.is_perishable || props.item.is_eternal),
)

const unlockText = computed(() => {
  if (!props.item) return ''
  return props.item.unlock_condition || props.item.unlock_factor?.description || ''
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
  if (busy.value || !props.item) return
  busy.value = true
  try {
    emit('manual-unlock', props.item)
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

/* MEJORA A — preview compacto del voucher upgraded. */
.upgrade-box {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 6px 4px;

  &__thumb {
    width: 60px;
    aspect-ratio: 71 / 95;
    object-fit: contain;
    border-radius: 6px;
    image-rendering: pixelated;
    flex-shrink: 0;
    background: rgba(0, 0, 0, 0.25);

    &--missing {
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'm6x11plus', monospace;
      font-size: 24px;
      color: $panel-light;
    }
  }

  &__name {
    font-family: 'm6x11plus', monospace;
    font-size: 14px;
    color: $text-1;
    letter-spacing: 0.3px;
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
