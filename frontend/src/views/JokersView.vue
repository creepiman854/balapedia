<!--
  Vista de Comodines.

  Pase 4:
    · Grid `gap: 0` → cartas pegadas, ocupan el 100% del ancho del
      .grid-scroll. El número de columnas (5..15) viene del store y se
      respeta tal cual; la carta dimensiona vía aspect-ratio.
    · Arco por fila: pasamos colIndex y colCount a cada JokerCard.
    · "Available from start" → siempre visible aunque el backend diga
      `unlocked_for_me: false` (caso típico: usuario nuevo que aún no
      ha sincronizado con Steam — debe ver los jokers de partida).

  El estado de desbloqueado real sigue siendo server-side (UserUnlock);
  el "available from start" es solo una whitelist visual del frontend
  basada en `unlock_condition` / `unlock_factor`.
-->
<template>
  <div class="jokers-view">
    <div class="view-title">▸ COMODINES</div>

    <div class="jokers-layout">
      <!-- ── Columna izquierda: grid ── -->
      <div class="jokers-grid-col">
        <ProgressBar
          v-if="isAuthenticated && jokers.length"
          :value="totalUnlocked"
          :max="jokers.length"
          color="#3b82f6"
          label="COMODINES DESBLOQUEADOS"
        />

        <FilterBar v-model="filters" />

        <div class="count">
          <template v-if="loading">Cargando comodines...</template>
          <template v-else-if="error">{{ error }}</template>
          <template v-else>{{ filtered.length }} comodines encontrados</template>
        </div>

        <div class="grid-scroll">
          <div
            v-if="!loading && !error"
            class="grid"
            :style="{
              gridTemplateColumns: `repeat(${settings.gridColumns}, 1fr)`,
            }"
          >
            <JokerCard
              v-for="(joker, idx) in filtered"
              :key="joker.id"
              :joker="joker"
              :is-locked="isLocked(joker)"
              :is-selected="selectedJoker?.id === joker.id"
              :col-index="idx % settings.gridColumns"
              :col-count="settings.gridColumns"
              @select="onSelect"
              @hover="onHover"
              @leave="onLeave"
            />
          </div>
        </div>
      </div>

      <!-- ── Columna derecha: detalle ── -->
      <div class="detail-col">
        <div class="detail-col__head">
          <span>{{ selectedJoker ? selectedJoker.name.toUpperCase() : 'COMODÍN' }}</span>
        </div>
        <div class="detail-col__body">
          <JokerDetailPanel
            :joker="selectedJoker"
            :is-locked="selectedJoker ? isLocked(selectedJoker) : false"
            @manual-unlock="onManualUnlock"
          />
        </div>
      </div>
    </div>

    <!-- Tooltip global flotante -->
    <JokerTooltip
      v-if="tooltip"
      :joker="tooltip.joker"
      :is-locked="isLocked(tooltip.joker)"
      :card-center-x="tooltip.cardCenterX"
      :card-top="tooltip.cardTop"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useBackgroundStore } from '@/stores/background'
import { fetchAllJokers, unlockJoker } from '@/services/jokers'
import { RARITY_ORDER } from '@/constants/rarity'

import ProgressBar from '@/components/common/ProgressBar.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import JokerCard from '@/components/jokers/JokerCard.vue'
import JokerDetailPanel from '@/components/jokers/JokerDetailPanel.vue'
import JokerTooltip from '@/components/jokers/JokerTooltip.vue'

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)
const settings = useSettingsStore()
const bgStore = useBackgroundStore()

// ── Datos ─────────────────────────────────────────────────────────────
const jokers = ref([])
const loading = ref(false)
const error = ref('')

async function loadJokers() {
  loading.value = true
  error.value = ''
  try {
    jokers.value = await fetchAllJokers({ authenticated: isAuthenticated.value })
    if (!selectedJoker.value && jokers.value.length) {
      selectedJoker.value = jokers.value[0]
    }
  } catch (e) {
    console.error('[JokersView] no se pudieron cargar los jokers', e)
    error.value = 'No se pudieron cargar los comodines. ¿Backend caído?'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // Le decimos al shader que pinte el preset "jokers" — esto es lo que
  // hará cada vista al montar (Tarot → 'tarot', Planet → 'planet', etc.).
  // El BalatroBackground interpola suavemente desde el preset anterior.
  bgStore.setPreset('jokers')
  loadJokers()
})
watch(isAuthenticated, loadJokers)

/**
 * Detecta jokers desbloqueados de fábrica ("Available from start").
 * Esto vive en el frontend como una whitelist visual: cualquier joker
 * que en su unlock_condition o unlock_factor contenga la frase NO se
 * marca como locked, aunque /api/me/jokers diga unlocked_for_me=false
 * (caso típico: usuario nuevo sin UserUnlock todavía).
 *
 * Si en el futuro el backend crea las UserUnlock rows automáticamente
 * para los starter jokers al hacer signup, esta función será un no-op
 * (todo `unlocked_for_me` ya sería true para esos).
 */
function isAvailableFromStart(joker) {
  const condition = String(
    joker.unlock_condition || joker.unlock_factor?.description || '',
  ).toLowerCase()
  if (
    condition.includes('available from start') ||
    condition.includes('available from the start') ||
    condition.includes('disponible desde el inicio')
  ) {
    return true
  }
  const code = String(joker.unlock_factor?.code || '').toLowerCase()
  return code === 'available_from_start' || code === 'start'
}

function isLocked(joker) {
  if (!isAuthenticated.value) return false
  if (isAvailableFromStart(joker)) return false
  if (!Object.prototype.hasOwnProperty.call(joker, 'unlocked_for_me')) return false
  return !joker.unlocked_for_me
}

// ── Manual unlock (botón en el panel de detalle) ─────────────────────
async function onManualUnlock(joker) {
  if (!joker) return
  try {
    await unlockJoker(joker.id)
    // Refrescamos toda la lista para que `unlocked_for_me` se actualice;
    // alternativa más fina sería mutar solo el joker afectado.
    await loadJokers()
    const fresh = jokers.value.find((j) => j.id === joker.id)
    if (fresh) selectedJoker.value = fresh
  } catch (e) {
    console.error('[JokersView] no se pudo desbloquear manualmente', e)
    alert('No se pudo marcar como desbloqueado. ¿Endpoint backend listo?')
  }
}

// ── Filtros ───────────────────────────────────────────────────────────
const filters = ref({
  search: '',
  rarity: 'all',
  status: 'all',
  sort: 'id',
})

function normalizeRarity(raw) {
  if (!raw || raw === 'all') return raw
  return String(raw).toUpperCase()
}

const filtered = computed(() => {
  const search = filters.value.search.toLowerCase()
  const rarityFilter = normalizeRarity(filters.value.rarity)
  return jokers.value
    .filter((j) => {
      const jr = String(j.rarity || '').toUpperCase()
      if (rarityFilter !== 'all' && jr !== rarityFilter) return false
      if (filters.value.status === 'unlocked' && isLocked(j)) return false
      if (filters.value.status === 'locked' && !isLocked(j)) return false
      if (
        search &&
        !(j.name || '').toLowerCase().includes(search) &&
        !(j.description || '').toLowerCase().includes(search)
      )
        return false
      return true
    })
    .sort((a, b) => {
      if (filters.value.sort === 'name') return (a.name || '').localeCompare(b.name || '')
      if (filters.value.sort === 'rarity') {
        const oa = RARITY_ORDER[String(a.rarity).toUpperCase()] ?? 99
        const ob = RARITY_ORDER[String(b.rarity).toUpperCase()] ?? 99
        return oa - ob
      }
      const oa = a.item_number ?? a.id
      const ob = b.item_number ?? b.id
      return oa - ob
    })
})

const totalUnlocked = computed(() => {
  if (!isAuthenticated.value) return jokers.value.length
  return jokers.value.filter((j) => !isLocked(j)).length
})

// ── Selección + tooltip ───────────────────────────────────────────────
const selectedJoker = ref(null)
const tooltip = ref(null)
let hoverTimer = null

function onSelect(joker) {
  selectedJoker.value = joker
}

function onHover({ joker, target }) {
  clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => {
    const rect = target.getBoundingClientRect()
    tooltip.value = {
      joker,
      cardCenterX: rect.left + rect.width / 2,
      cardTop: rect.top,
    }
  }, 120)
}

function onLeave() {
  clearTimeout(hoverTimer)
  tooltip.value = null
}

onBeforeUnmount(() => clearTimeout(hoverTimer))
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;
@use '@/assets/styles/mixins' as *;

.jokers-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/*
 * Textos que viven SOBRE el shader (fuera de cualquier panel oscuro):
 *   .view-title  · .count
 * Blancos con drop-shadow sólido sin desenfoque (text-shadow 0 5px 0 #000),
 * tamaño aumentado, letterspacing un poco más holgado. Así son legibles
 * sin importar si el shader detrás tiene rojo, azul o teal oscuro.
 */
.view-title {
  font-family: 'm6x11plus', monospace;
  font-size: 22px;
  color: #ffffff;
  text-shadow: 0 2px 0 #00000070;
  letter-spacing: 1px;
  margin-bottom: 14px;
  padding-left: 4px;
}

.jokers-layout {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.jokers-grid-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.count {
  font-family: 'm6x11plus', monospace;
  font-size: 16px;
  color: #ffffff;
  text-shadow: 0 2px 0 #00000070;
  margin-bottom: 10px;
  padding-left: 4px;
  letter-spacing: 0.4px;
}

/*
 * El grid-scroll ahora actúa como "panel" translúcido: deja ver el
 * shader detrás pero da contorno y soporte visual a las cartas para
 * que no se vean tan sueltas sobre el fondo animado.
 *
 * - rgba(panel-darkest, 0.6) → transparencia controlada.
 * - pixel-clip → mismas esquinas de los demás paneles.
 * - Padding interior generoso para que zoom/tilt no se corte.
 */
.grid-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 28px 22px 32px;
  background: rgba(26, 42, 46, 0.6); // = $panel-darkest con alpha
  scrollbar-width: thin;
  scrollbar-color: $panel-mid transparent;
  @include pixel-clip;
}

/*
 * gap: 0 → las cartas se tocan (look del juego con cartas pegadas).
 * row-gap pequeño para que el arco por fila respire.
 */
.grid {
  display: grid;
  gap: 0;
  row-gap: 16px;
}

.detail-col {
  width: 340px;
  flex-shrink: 0;
  background: $panel-darkest;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px $shadow;
  @include pixel-clip;

  &__head {
    background: $panel-mid;
    padding: 10px 14px;
    text-align: center;
    border-bottom: 2px solid $panel-medlight;

    span {
      font-family: 'm6x11plus', monospace;
      font-size: 14px;
      color: $text-1;
      letter-spacing: 1px;
    }
  }

  &__body {
    flex: 1;
    overflow: hidden;
  }
}
</style>
