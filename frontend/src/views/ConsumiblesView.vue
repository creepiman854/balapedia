<!--
  Vista de Consumibles.

  Tres sub-tabs (Tarot, Planet, Spectral). Cada cambio:
    1. Setea el preset del shader del fondo (`tarot` | `planet` | `spectral`),
       que anima los colores en 700 ms.
    2. Limpia el filtro de búsqueda y la selección.
    3. Carga las cartas del tipo correspondiente desde
       /api/consumables?type=...

  Diferencias con JokersView (deliberadas):
    · Grid con número de columnas FIJO (7) — el slider del settings
      modal solo aplica a Jokers, según convención del juego.
    · FilterBar reducido a search + sort (no hay rareza ni
      unlocked/locked overlay todavía).
    · `ItemDetailPanel` recibe `canUnlock=false`: el endpoint
      `/api/me/consumables` no existe aún, así que no tendría sentido
      mostrar el botón de desbloqueo manual.
-->
<template>
  <div class="consumibles-view">
    <!-- <div class="view-title">▸ CONSUMIBLES</div> -->

    <div class="layout">
      <!-- ── Grid izquierda ── -->
      <div class="grid-col">
        <!--
          Toolbar: sub-tabs a la IZQUIERDA del FilterBar (mismo
          patrón que CollectionView). En consumibles no añadimos
          ProgressBar — todos los items son "Available from start".
        -->
        <div class="toolbar">
          <div class="subtabs">
            <button
              v-for="sub in SUBTABS"
              :key="sub.id"
              :class="['subtab', `subtab--${sub.id}`, { 'subtab--active': currentSub === sub.id }]"
              :style="currentSub === sub.id
                ? { boxShadow: `0 4px 16px ${sub.color}55, inset 0 -2px 0 rgba(0,0,0,0.3)` }
                : { filter: 'brightness(0.7) saturate(0.65)' }"
              @click="selectSub(sub.id)"
            >
              {{ sub.label }}
            </button>
          </div>

          <FilterBar
            v-model="filters"
            :enabled="['search', 'sort']"
            search-placeholder="Buscar carta..."
          />
        </div>

        <div class="count">
          <template v-if="loading">Cargando {{ currentSubLabel.toLowerCase() }}...</template>
          <template v-else-if="error">{{ error }}</template>
          <template v-else>{{ filtered.length }} cartas encontradas</template>
        </div>

        <div class="grid-scroll">
          <div
            v-if="!loading && !error"
            class="grid"
            :style="{ gridTemplateColumns: `repeat(${FIXED_COLS}, 1fr)` }"
          >
            <ItemCard
              v-for="(item, idx) in filtered"
              :key="item.id"
              :item="item"
              :is-locked="false"
              :is-selected="selectedItem?.id === item.id"
              :col-index="idx % FIXED_COLS"
              :col-count="FIXED_COLS"
              @select="onSelect"
              @hover="onHover"
              @leave="onLeave"
            />
          </div>
        </div>
      </div>

      <!-- ── Detalle derecha ── -->
      <div class="detail-col">
        <div class="detail-col__head">
          <span>{{ selectedItem ? selectedItem.name.toUpperCase() : currentSubLabel.toUpperCase() }}</span>
        </div>
        <div class="detail-col__body">
          <ItemDetailPanel
            :item="selectedItem"
            :is-locked="false"
            :can-unlock="false"
          />
        </div>
      </div>
    </div>

    <!-- Tooltip flotante -->
    <ItemTooltip
      v-if="tooltip"
      :item="tooltip.item"
      :is-locked="false"
      :card-center-x="tooltip.cardCenterX"
      :card-top="tooltip.cardTop"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useBackgroundStore } from '@/stores/background'
import { fetchConsumablesByType } from '@/services/consumables'

import FilterBar from '@/components/common/FilterBar.vue'
import ItemCard from '@/components/items/ItemCard.vue'
import ItemDetailPanel from '@/components/items/ItemDetailPanel.vue'
import ItemTooltip from '@/components/items/ItemTooltip.vue'

const bgStore = useBackgroundStore()

/* ── Sub-tabs ───────────────────────────────────────────────────────
 * El `id` aquí coincide con:
 *   - el `type` que el endpoint /api/consumables espera
 *     (UPPERCASE: TAROT / PLANET / SPECTRAL).
 *   - el nombre del preset de shader (`tarot` / `planet` / `spectral`),
 *     que se pasa toLowerCase().
 */
const SUBTABS = [
  { id: 'TAROT',    label: 'TAROT',     color: '#D8B062' },
  { id: 'PLANET',   label: 'PLANETA',   color: '#4790A1' },
  { id: 'SPECTRAL', label: 'ESPECTRAL', color: '#5066A5' },
]

const FIXED_COLS = 7
const currentSub = ref('TAROT')

const currentSubLabel = computed(
  () => SUBTABS.find((s) => s.id === currentSub.value)?.label || '',
)

function selectSub(id) {
  if (currentSub.value === id) return
  currentSub.value = id
  // Reset interno antes de cargar — evita ver datos del subtab anterior.
  items.value = []
  selectedItem.value = null
  tooltip.value = null
  filters.value = { search: '', sort: 'id' }
  bgStore.setPreset(id.toLowerCase())
  loadItems()
}

// ── Datos ─────────────────────────────────────────────────────────
const items = ref([])
const loading = ref(false)
const error = ref('')

async function loadItems() {
  loading.value = true
  error.value = ''
  try {
    items.value = await fetchConsumablesByType(currentSub.value)
    if (!selectedItem.value && items.value.length) {
      selectedItem.value = items.value[0]
    }
  } catch (e) {
    console.error('[ConsumiblesView] error completo:', e, e.cause || '')
    // Mostramos el mensaje real (status + detail) que arma el servicio.
    // Si el backend devuelve 400 "invalid: 'TAROT'" se ve tal cual y
    // podemos diagnosticar al instante.
    error.value = e.message || 'Error desconocido al cargar las cartas.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  bgStore.setPreset(currentSub.value.toLowerCase())
  loadItems()
})

// Si el usuario cambia de cuenta mientras está en esta vista, el
// catálogo público no cambia, no recargamos.

// ── Filtros ───────────────────────────────────────────────────────
const filters = ref({
  search: '',
  sort: 'id',
})

const filtered = computed(() => {
  const search = filters.value.search.toLowerCase()
  return items.value
    .filter((it) => {
      if (
        search &&
        !(it.name || '').toLowerCase().includes(search) &&
        !(it.description || '').toLowerCase().includes(search)
      )
        return false
      return true
    })
    .sort((a, b) => {
      if (filters.value.sort === 'name') return (a.name || '').localeCompare(b.name || '')
      const oa = a.item_number ?? a.id
      const ob = b.item_number ?? b.id
      return oa - ob
    })
})

// ── Selección + tooltip ───────────────────────────────────────────
const selectedItem = ref(null)
const tooltip = ref(null)
let hoverTimer = null

function onSelect(item) {
  selectedItem.value = item
}

function onHover({ item, target }) {
  clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => {
    const rect = target.getBoundingClientRect()
    tooltip.value = {
      item,
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

.consumibles-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.view-title {
  font-family: 'm6x11plus', monospace;
  font-size: 22px;
  color: #ffffff;
  text-shadow: 0 3px 0 #00000070;
  letter-spacing: 1px;
  margin-bottom: 14px;
  padding-left: 4px;
}

/* ── Sub-tabs ─────────────────────────────────────────────────── */
/* Toolbar: subtabs + filter bar en una misma fila. */
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  align-items: stretch;

  /* El FilterBar es un componente hijo — pierce scoped con :deep. */
  :deep(.filterbar) {
    flex: 1;
    min-width: 0;
  }
}

.subtabs {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.subtab {
  font-family: 'm6x11plus', monospace;
  font-size: 13px;
  color: #fff;
  border: none;
  padding: 10px 16px;
  cursor: pointer;
  letter-spacing: 1px;
  text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.6);
  transition: transform 0.1s, filter 0.1s;
  white-space: nowrap;
  @include pixel-clip;

  &:hover { transform: scale(1.05); filter: brightness(1.15); }
  &:active { transform: scale(0.95); }
}
.subtab--TAROT    { background: #d97706; }
.subtab--PLANET   { background: #4790a1; }
.subtab--SPECTRAL { background: #5066a5; }
.subtab--active   { filter: brightness(1.25); }

/* ── Layout ───────────────────────────────────────────────────── */
.layout {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.grid-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.count {
  font-family: 'm6x11plus', monospace;
  font-size: 16px;
  color: #ffffff;
  text-shadow: 0 3px 0 #00000070;
  margin-bottom: 10px;
  padding-left: 4px;
  letter-spacing: 0.4px;
}

.grid-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 28px 22px 32px;
  background: rgba(26, 42, 46, 0.6);
  scrollbar-width: thin;
  scrollbar-color: $panel-mid transparent;
  @include pixel-clip;
}

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
