<!--
  Vista de Comodines.

  Flujo de datos:
    · Sin sesión   → GET /api/jokers              (todos visibles, sin overlay)
    · Con sesión   → GET /api/me/jokers           (overlay `unlocked_for_me`)

  El estado de "desbloqueado" NO es manipulable desde el cliente. Procede
  de UserUnlock en BD, que se actualiza vía sync con Steam (rama
  feat/steam-sync del backend). El click sobre una carta solo selecciona
  para mostrar el panel de detalle.

  Si en futuro hay que reaccionar a un re-sync (refrescar el grid), basta
  con volver a llamar a `loadJokers()`.
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
              gridTemplateColumns:
                settings.jokerColumns > 0
                  ? `repeat(${settings.jokerColumns}, 1fr)`
                  : 'repeat(auto-fill, minmax(130px, 1fr))',
            }"
          >
            <JokerCard
              v-for="joker in filtered"
              :key="joker.id"
              :joker="joker"
              :is-locked="isLocked(joker)"
              :is-selected="selectedJoker?.id === joker.id"
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
import { fetchAllJokers } from '@/services/jokers'
import { RARITY_ORDER, getRarity } from '@/constants/rarity'

import ProgressBar from '@/components/common/ProgressBar.vue'
import FilterBar from '@/components/common/FilterBar.vue'
import JokerCard from '@/components/jokers/JokerCard.vue'
import JokerDetailPanel from '@/components/jokers/JokerDetailPanel.vue'
import JokerTooltip from '@/components/jokers/JokerTooltip.vue'

const authStore = useAuthStore()
const { isAuthenticated } = storeToRefs(authStore)
const settings = useSettingsStore()

// ── Datos ─────────────────────────────────────────────────────────────
const jokers = ref([])
const loading = ref(false)
const error = ref('')

/**
 * Carga inicial + recarga cuando cambia el estado de auth (al loguear o
 * desloguear queremos refrescar para incluir/excluir el overlay).
 */
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

onMounted(loadJokers)
watch(isAuthenticated, loadJokers)

/**
 * Un joker está "bloqueado" para el usuario actual cuando hay sesión y el
 * backend nos dice explícitamente `unlocked_for_me: false`. Sin sesión
 * (servimos desde /api/jokers) NO marcamos nada como bloqueado — la
 * encyclopedia se ve completa.
 */
function isLocked(joker) {
  if (!isAuthenticated.value) return false
  // El campo solo viene en /api/me/jokers. Si no aparece, fallback a
  // mostrarlo desbloqueado (mejor que ocultar todo).
  if (!Object.prototype.hasOwnProperty.call(joker, 'unlocked_for_me')) return false
  return !joker.unlocked_for_me
}

// ── Filtros ───────────────────────────────────────────────────────────
const filters = ref({
  search: '',
  rarity: 'all',
  status: 'all',
  sort: 'id',
})

/**
 * Los filtros usan los nombres del backend en UPPERCASE para que
 * coincidan con el `rarity` que llega. Si el FilterBar pasa los valores
 * en lowercase del mock viejo ('common'), normalizamos por compatibilidad
 * mientras no se actualice ese componente.
 */
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
      // 'id' usa el item_number del backend si está; si no, id.
      const oa = a.item_number ?? a.id
      const ob = b.item_number ?? b.id
      return oa - ob
    })
})

const totalUnlocked = computed(() => {
  if (!isAuthenticated.value) return jokers.value.length
  return jokers.value.filter((j) => j.unlocked_for_me).length
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

// Re-exportamos getRarity sólo si la plantilla lo necesita en el futuro;
// los componentes hijos ya lo importan directamente.
void getRarity
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

.view-title {
  font-family: 'm6x11plus', monospace;
  font-size: 13px;
  color: $text-3;
  letter-spacing: 1px;
  margin-bottom: 10px;
  padding-left: 2px;
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
  font-size: 11px;
  color: $panel-light;
  margin-bottom: 8px;
  padding-left: 4px;
}

.grid-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  scrollbar-width: thin;
  scrollbar-color: $panel-mid $panel-darkest;
}

.grid {
  display: grid;
  gap: 10px;
  padding-bottom: 20px;
}

.detail-col {
  width: 260px;
  flex-shrink: 0;
  background: $panel-darkest;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px $shadow;
  @include pixel-clip;

  &__head {
    background: $panel-mid;
    padding: 8px 12px;
    text-align: center;
    border-bottom: 2px solid $panel-medlight;

    span {
      font-family: 'm6x11plus', monospace;
      font-size: 13px;
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
