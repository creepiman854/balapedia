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
  <div class="consumables-view">
    <div class="layout">
      <!-- ── Grid izquierda ── -->
      <div class="grid-col" style="position: relative">
        <!--
          Toolbar: sub-tabs a la IZQUIERDA del FilterBar (mismo
          patrón que CollectionView). En consumables no añadimos
          ProgressBar — todos los items son "Available from start".
        -->
        <div class="toolbar">
          <div class="subtabs">
            <button
              v-for="sub in SUBTABS"
              :key="sub.id"
              :class="['subtab', `subtab--${sub.id}`, { 'subtab--active': currentSub === sub.id }]"
              :style="
                currentSub === sub.id
                  ? { boxShadow: `0 4px 16px ${sub.color}55, inset 0 -2px 0 rgba(0,0,0,0.3)` }
                  : { filter: 'brightness(0.7) saturate(0.65)' }
              "
              @click="selectSub(sub.id)"
            >
              {{ sub.label }}
            </button>
          </div>

          <FilterBar
            v-model="filters"
            :enabled="['search', 'sort']"
            search-placeholder="Search card..."
          />
        </div>

        <div class="count">
          <template v-if="loading">Loading {{ currentSubLabel.toLowerCase() }}...</template>
          <template v-else-if="error">{{ error }}</template>
          <template v-else>{{ filtered.length }} cards found</template>
        </div>

        <BalatroLoader v-if="showLoader" :is-loading="loading" @hidden="showLoader = false" />

        <div class="grid-scroll" ref="scrollEl">
          <div
            v-if="!loading && !error && filtered.length > 0"
            class="grid"
            :style="{ gridTemplateColumns: `repeat(${activeCols}, 1fr)` }"
          >
            <ItemCard
              v-for="(item, idx) in filtered"
              :key="item.id"
              class="card-deal-anim"
              :style="{ animationDelay: `${Math.min(idx, 50) * 35}ms` }"
              :item="item"
              :is-locked="false"
              :is-selected="selectedItem?.id === item.id"
              :col-index="idx % activeCols"
              :col-count="activeCols"
              @select="onSelect"
              @hover="onHover"
              @leave="onLeave"
            />
          </div>
          <div v-if="!loading && !error && filtered.length === 0" class="empty">
            No cards found with those filters.
          </div>
        </div>
      </div>

      <!-- Backdrop del bottom sheet (solo se ve cuando está abierto en móvil/tablet) -->
      <div v-if="detailSheetOpen" class="detail-backdrop" @click="closeDetailSheet" />

      <!-- ── Detalle derecha ── -->
      <div class="detail-col" :class="{ 'detail-col--open': detailSheetOpen }">
        <div class="detail-col__head">
          <span>{{
            selectedItem ? selectedItem.name.toUpperCase() : currentSubLabel.toUpperCase()
          }}</span>
          <button class="detail-col__close" @click="closeDetailSheet" aria-label="Close">
            <iconify-icon icon="pixel:window-close-solid" noobserver />
          </button>
        </div>
        <div class="detail-col__body">
          <ItemDetailPanel :item="selectedItem" :is-locked="false" :can-unlock="false" />
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
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useBackgroundStore } from "@/stores/background";
import { fetchConsumablesByType } from "@/services/consumables";
import { useHideHeaderOnScroll } from "@/composables/useHideHeaderOnScroll";

import FilterBar from "@/components/common/FilterBar.vue";
import ItemCard from "@/components/items/ItemCard.vue";
import ItemDetailPanel from "@/components/items/ItemDetailPanel.vue";
import ItemTooltip from "@/components/items/ItemTooltip.vue";
import BalatroLoader from "@/components/common/BalatroLoader.vue";

const bgStore = useBackgroundStore();

// Ref al contenedor scrollable → composable que oculta AppHeader en móvil.
const scrollEl = ref(null);
useHideHeaderOnScroll(scrollEl);

/* ── Sub-tabs ───────────────────────────────────────────────────────
 * El `id` aquí coincide con:
 *   - el `type` que el endpoint /api/consumables espera
 *     (UPPERCASE: TAROT / PLANET / SPECTRAL).
 *   - el nombre del preset de shader (`tarot` / `planet` / `spectral`),
 *     que se pasa toLowerCase().
 */
const SUBTABS = [
  { id: "TAROT", label: "TAROT", color: "#D8B062" },
  { id: "PLANET", label: "PLANET", color: "#4790A1" },
  { id: "SPECTRAL", label: "SPECTRAL", color: "#5066A5" },
];

const FIXED_COLS = 7;
const currentSub = ref("TAROT");

// Variable reactiva que detectará si estamos en móvil o no
const activeCols = ref(FIXED_COLS);
const currentSubLabel = computed(() => SUBTABS.find((s) => s.id === currentSub.value)?.label || "");

// Referencias para el listener
let mql = null;
let updateCols = null;

function selectSub(id) {
  if (currentSub.value === id) return;
  currentSub.value = id;
  // Reset interno antes de cargar — evita ver datos del subtab anterior.
  items.value = [];
  selectedItem.value = null;
  tooltip.value = null;
  filters.value = { search: "", sort: "id" };
  bgStore.setPreset(id.toLowerCase());
  loadItems();
}

// ── Datos ─────────────────────────────────────────────────────────
const items = ref([]);
const loading = ref(false);
const showLoader = ref(true);
const error = ref("");

const detailSheetOpen = ref(false);

async function loadItems() {
  loading.value = true;
  showLoader.value = true;
  error.value = "";
  try {
    items.value = await fetchConsumablesByType(currentSub.value);
    if (!selectedItem.value && items.value.length) {
      selectedItem.value = items.value[0];
    }
  } catch (e) {
    console.error("[ConsumiblesView] error completo:", e, e.cause || "");
    // Mostramos el mensaje real (status + detail) que arma el servicio.
    // Si el backend devuelve 400 "invalid: 'TAROT'" se ve tal cual y
    // podemos diagnosticar al instante.
    error.value = e.message || "Unknown error while loading cards.";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  bgStore.setPreset(currentSub.value.toLowerCase());
  loadItems();

  // Esto garantiza que solo afecte a móvil (< 600px)
  mql = window.matchMedia("(max-width: 599px)");
  updateCols = (e) => {
    // Si es móvil (matches), usa 4 columnas. Si es Tablet/PC, usa FIXED_COLS (7).
    activeCols.value = e.matches ? 4 : FIXED_COLS;
  };
  mql.addEventListener("change", updateCols);
  updateCols(mql); // Comprobación inicial al cargar
});

// Si el usuario cambia de cuenta mientras está en esta vista, el
// catálogo público no cambia, no recargamos.

// ── Filtros ───────────────────────────────────────────────────────
const filters = ref({
  search: "",
  sort: "id",
});

const filtered = computed(() => {
  const search = filters.value.search.toLowerCase();
  return items.value
    .filter((it) => {
      if (
        search &&
        !(it.name || "").toLowerCase().includes(search) &&
        !(it.description || "").toLowerCase().includes(search)
      )
        return false;
      return true;
    })
    .sort((a, b) => {
      if (filters.value.sort === "name") return (a.name || "").localeCompare(b.name || "");
      const oa = a.item_number ?? a.id;
      const ob = b.item_number ?? b.id;
      return oa - ob;
    });
});

// ── Selección + tooltip ───────────────────────────────────────────
const selectedItem = ref(null);
const tooltip = ref(null);
let hoverTimer = null;

function onSelect(item) {
  selectedItem.value = item;
  // En desktop el panel ya está visible; abrir el sheet solo cambia
  // estado interno que el CSS aplica solo en tablet/mobile.
  detailSheetOpen.value = true;
}

function closeDetailSheet() {
  detailSheetOpen.value = false;
  // No desmarcamos selectedJoker — al cerrar y reabrir mantiene la carta
  // selecciondaa visible en el panel.
}

function onHover({ item, target }) {
  clearTimeout(hoverTimer);
  hoverTimer = setTimeout(() => {
    const rect = target.getBoundingClientRect();
    tooltip.value = {
      item,
      cardCenterX: rect.left + rect.width / 2,
      cardTop: rect.top,
    };
  }, 120);
}

function onLeave() {
  clearTimeout(hoverTimer);
  tooltip.value = null;
}

onBeforeUnmount(() => {
  clearTimeout(hoverTimer);
  if (mql && updateCols) {
    mql.removeEventListener("change", updateCols);
  }
});
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.consumables-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.view-title {
  font-family: "m6x11plus", monospace;
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
  font-family: "m6x11plus", monospace;
  font-size: 13px;
  color: #fff;
  border: none;
  padding: 10px 16px;
  cursor: pointer;
  letter-spacing: 1px;
  text-shadow: 1px 1px 0 rgba(0, 0, 0, 0.6);
  transition:
    transform 0.1s,
    filter 0.1s;
  white-space: nowrap;
  @include pixel-clip;

  @include can-hover {
    &:hover {
      transform: scale(1.05);
      filter: brightness(1.15);
    }
  }
  &:active {
    transform: scale(0.95);
  }
}
.subtab--TAROT {
  background: #d97706;
}
.subtab--PLANET {
  background: #4790a1;
}
.subtab--SPECTRAL {
  background: #5066a5;
}
.subtab--active {
  filter: brightness(1.25);
}

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
  font-family: "m6x11plus", monospace;
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
      font-family: "m6x11plus", monospace;
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

.empty {
  color: $text-3;
  font-family: "m6x11plus", monospace;
  font-size: 14px;
  text-align: center;
  padding: 24px 0;
}

/* ── Animaciones de Entrada ───────────────────────────────────────── */
.card-deal-anim {
  animation: dealCard 0.45s cubic-bezier(0.175, 0.885, 0.32, 1.15) backwards;
}

@keyframes dealCard {
  0% {
    opacity: 0;
    translate: 0 -100px;
    scale: 1.15;
  }
  100% {
    opacity: 1;
    translate: 0 0;
    scale: 1;
  }
}

/* ── Botón cerrar del bottom sheet — invisible en desktop ─────── */
.detail-col__head {
  position: relative;
}

.detail-col__close {
  display: none; // Default: desktop, NO se ve.
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  background: transparent;
  border: none;
  color: $text-2;
  cursor: pointer;
  padding: 4px;
  line-height: 0;

  iconify-icon {
    font-size: 22px;
  }

  @include can-hover {
    &:hover {
      color: $text-1;
    }
  }
}

/* ── Backdrop del bottom sheet ──────────────────────────────── */
.detail-backdrop {
  display: none; // Default: desktop, no aplica.
  position: fixed;
  inset: 0;
  background: rgba(10, 15, 18, 0.75);
  z-index: 8500;
  animation: backdropIn 0.18s ease;
}

@keyframes backdropIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* ──────────────────────────────────────────────────────────────
 * TABLET — layout una columna + bottom sheet.
 * ────────────────────────────────────────────────────────────── */
@include tablet {
  .layout {
    flex-direction: column;
  }

  // FIX (scroll): añadimos min-height:0 al wrapper intermedio para que
  // el .grid-scroll interno pueda activar su overflow-y:auto cuando
  // el contenido excede la pantalla.
  .grid-col {
    width: 100%;
    min-height: 0;
  }

  .toolbar {
    flex-direction: column;
    gap: 8px;
  }

  .subtabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
    padding-bottom: 2px;
    -webkit-overflow-scrolling: touch;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  .grid-scroll {
    padding: 18px 14px 24px;
  }

  .detail-col {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    top: auto;
    width: 100%;
    max-height: 85vh;
    z-index: 8600;
    transform: translateY(100%);
    transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
    clip-path: none;

    &--open {
      transform: translateY(0);
    }

    &__close {
      display: inline-flex;
    }

    &__body {
      overflow-y: auto;
      overflow-x: hidden;
      -webkit-overflow-scrolling: touch;
    }
  }

  .detail-backdrop {
    display: block;
  }
}

/* ──────────────────────────────────────────────────────────────
 * MOBILE — consumables tiene grid FIJO en desktop (7 cols). En
 * móvil bajamos a 4 col porque a partir de ahí los iconos no se
 * leen. No es configurable por el usuario, no aplica slider.
 * ────────────────────────────────────────────────────────────── */
@include mobile {
  .grid-scroll {
    padding: 14px 10px 20px;
  }

  // !important porque el grid-template-columns viene como inline
  // style desde el template (repeat(7, 1fr)).
  .grid {
    grid-template-columns: repeat(4, 1fr) !important;
  }

  .count {
    font-size: 14px;
  }

  .subtab {
    font-size: 12px;
    padding: 8px 12px;
  }

  .detail-col {
    max-height: 90vh;
  }
}
</style>
