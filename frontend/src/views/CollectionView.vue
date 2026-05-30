<!--
  Vista de COLECCIÓN.

  Subtabs (Fase 3):
    DECKS         → barajas regulares + sección Challenge Decks abajo.
    BOOSTER PACKS → 5 grupos por pack_type.
    VOUCHERS      → base/upgraded.
    CARD MODIFIERS → Enhancements/Editions/Seals.
    BLINDS        → fila destacada (Small + Big) + grid Boss/Finisher.
    TAGS          → grid de 24 tags.

  Reglas de diseño preservadas:
    · Carga sub-tabs en SECUENCIA (max_user_connections=5 del pool MySQL).
    · BLINDS y TAGS no son Unlockable: cuentan en la barra de progreso
      global como "siempre desbloqueados" (decisión de UX para que la %
      refleje la presencia total en la app).
    · Challenge Decks SÍ son Unlockable: contribuyen al lock-state real
      vía Rule Breaker (BAL_23) o desbloqueo manual.
    · El detail-col se oculta en BLINDS y TAGS — la info se sirve
      exclusivamente via tooltip flotante (ItemTooltip con kind='blind'
      o kind='tag'). En el resto, ItemDetailPanel como hasta ahora.

  Lock-state:
    · Para Unlockables (decks/vouchers/packs/challenge-decks) → isItemLocked
    · Para Blinds/Tags → siempre false (no son Unlockable).
-->
<template>
  <div class="collection-view">
    <div class="layout" :class="{ 'layout--full': isFullWidth }">
      <!-- ── Columna izquierda ── -->
      <div class="grid-col" style="position: relative">
        <!-- Progress bar global (suma de todos los sub-tabs) -->
        <ProgressBar
          v-if="isAuthenticated && globalTotal > 0"
          :value="globalUnlocked"
          :max="globalTotal"
          color="#22c55e"
          label="COLLECTION UNLOCKED"
        />

        <!-- Toolbar: sub-tabs + filtros -->
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
            :enabled="enabledFilters"
            :type-options="typeOptions"
            :size-options="sizeOptions"
            :search-placeholder="`Search ${currentSubLabel.toLowerCase()}...`"
          />
        </div>

        <div class="count">
          <template v-if="loading">Loading collection...</template>
          <template v-else-if="error">{{ error }}</template>
          <template v-else>{{ subtabCount }} items found</template>
        </div>

        <BalatroLoader v-if="showLoader" :is-loading="loading" @hidden="showLoader = false" />

        <div class="grid-scroll" ref="scrollEl">
          <!-- ============ MAZOS + CHALLENGE DECKS ============ -->
          <div v-if="!loading && !error && currentSub === 'decks'" class="sectioned section--decks">
            <!-- Sección BARAJAS regulares -->
            <section
              v-if="!filters.type || filters.type === 'all' || filters.type === 'normal'"
              class="mod-section"
            >
              <header class="mod-section__head" style="color: #e84040">
                DECKS
                <span class="mod-section__count">{{ filteredDecks.length }}</span>
              </header>
              <div
                v-if="filteredDecks.length"
                class="grid mod-section__grid"
                :style="{ gridTemplateColumns: `repeat(${effectiveDeckCols}, 1fr)` }"
              >
                <ItemCard
                  v-for="(item, idx) in filteredDecks"
                  :key="`deck-${item.id}`"
                  class="card-deal-anim"
                  :style="{ animationDelay: `${Math.min(idx, 30) * 35}ms` }"
                  :item="item"
                  :is-locked="isLocked(item)"
                  :is-selected="selectedItem?.id === item.id && selectedItem?._kind === 'deck'"
                  :col-index="idx % effectiveDeckCols"
                  :col-count="effectiveDeckCols"
                  :stack="true"
                  @select="onSelect($event, 'deck')"
                  @hover="onHover"
                  @leave="onLeave"
                />
              </div>
              <p v-else class="mod-section__empty">— no items —</p>
            </section>

            <!-- Sección CHALLENGE DECKS -->
            <section
              v-if="!filters.type || filters.type === 'all' || filters.type === 'challenge'"
              class="mod-section"
            >
              <header class="mod-section__head" style="color: #8b5cf6">
                CHALLENGE DECKS
                <span class="mod-section__count">{{ filteredChallengeDecks.length }}</span>
              </header>
              <div
                v-if="filteredChallengeDecks.length"
                class="grid mod-section__grid"
                :style="{ gridTemplateColumns: `repeat(${effectiveDeckCols}, 1fr)` }"
              >
                <ItemCard
                  v-for="(item, idx) in filteredChallengeDecks"
                  :key="`challenge-${item.id}`"
                  class="card-deal-anim"
                  :style="{ animationDelay: `${Math.min(idx, 30) * 35}ms` }"
                  :item="item"
                  :is-locked="isLocked(item)"
                  :is-selected="
                    selectedItem?.id === item.id && selectedItem?._kind === 'challenge_deck'
                  "
                  :col-index="idx % effectiveDeckCols"
                  :col-count="effectiveDeckCols"
                  @select="onSelect($event, 'challenge_deck')"
                  @hover="onHover"
                  @leave="onLeave"
                />
              </div>
              <p v-else class="mod-section__empty">— no items —</p>
            </section>
          </div>

          <!-- ============ SOBRES (booster packs) ============ -->
          <div v-else-if="!loading && !error && currentSub === 'booster-packs'" class="packs-rows">
            <div
              v-for="(row, ri) in packRows"
              :key="ri"
              :class="['packs-row', { 'packs-row--solo': row.length === 1 }]"
            >
              <section v-for="group in row" :key="group.packType" class="pack-section">
                <header class="pack-section__head" :style="{ color: group.color }">
                  {{ group.label }}
                </header>
                <div
                  v-if="group.items.length"
                  class="grid pack-section__grid"
                  :style="{ gridTemplateColumns: `repeat(${effectivePackCols}, 1fr)` }"
                >
                  <ItemCard
                    v-for="(pack, idx) in group.items"
                    :key="pack.id"
                    class="card-deal-anim"
                    :style="{ animationDelay: `${Math.min(idx, 50) * 35}ms` }"
                    :item="enrichedPackName(pack)"
                    :is-locked="isLocked(pack)"
                    :is-selected="selectedItem?.id === pack.id && selectedItem?._kind === 'pack'"
                    :col-index="idx % effectivePackCols"
                    :col-count="effectivePackCols"
                    @select="onSelect($event, 'pack')"
                    @hover="onHover"
                    @leave="onLeave"
                  />
                </div>
                <p v-else class="mod-section__empty">— no items —</p>
              </section>
            </div>
          </div>

          <!-- ============ VALES (vouchers) ============ -->
          <div
            v-else-if="!loading && !error && currentSub === 'vouchers'"
            class="section--vouchers"
          >
            <div
              v-if="filteredVouchers.length"
              class="grid"
              :style="{ gridTemplateColumns: `repeat(${effectiveVoucherCols}, 1fr)` }"
            >
              <ItemCard
                v-for="(item, idx) in filteredVouchers"
                :key="item.id"
                class="card-deal-anim"
                :style="{ animationDelay: `${Math.min(idx, 50) * 35}ms` }"
                :item="item"
                :is-locked="isLocked(item)"
                :is-selected="selectedItem?.id === item.id && selectedItem?._kind === 'voucher'"
                :col-index="idx % effectiveVoucherCols"
                :col-count="effectiveVoucherCols"
                @select="onSelect($event, 'voucher')"
                @hover="onHover"
                @leave="onLeave"
              />
            </div>
            <p v-else class="mod-section__empty">— no items —</p>
          </div>

          <!-- ============ MEJORAS (card modifiers) ============ -->
          <div
            v-else-if="!loading && !error && currentSub === 'card-modifiers'"
            class="sectioned section--modifiers"
          >
            <section
              v-for="modGroup in filteredModifierGroups"
              :key="modGroup.key"
              class="mod-section"
            >
              <header class="mod-section__head" :style="{ color: modGroup.color }">
                {{ modGroup.label }}
                <span class="mod-section__count">{{ modGroup.items.length }}</span>
              </header>
              <div
                v-if="modGroup.items.length"
                class="grid mod-section__grid"
                :style="{ gridTemplateColumns: `repeat(${effectiveModCols}, 1fr)` }"
              >
                <ItemCard
                  v-for="(mod, idx) in modGroup.items"
                  :key="`${modGroup.key}-${mod.id}`"
                  class="card-deal-anim"
                  :style="{ animationDelay: `${Math.min(idx, 50) * 35}ms` }"
                  :item="mod"
                  :is-locked="isLocked(mod)"
                  :is-selected="
                    selectedItem?.id === mod.id &&
                    selectedItem?._kind === 'modifier' &&
                    selectedItem?._modKey === modGroup.key
                  "
                  :col-index="idx % effectiveModCols"
                  :col-count="effectiveModCols"
                  @select="onSelect($event, 'modifier', modGroup.key)"
                  @hover="onHover"
                  @leave="onLeave"
                />
              </div>
              <p v-else class="mod-section__empty">— no items —</p>
            </section>
          </div>

          <!-- ============ BLINDS ============ -->
          <div v-else-if="!loading && !error && currentSub === 'blinds'" class="blinds-wrapper">
            <!-- Tabla lateral de Antes -->
            <aside class="ante-sidebar">
              <header class="ante-sidebar__head">
                <span style="color: #f0a020">ANTE</span>
                <span style="color: #e84040">BASE</span>
              </header>
              <ul class="ante-sidebar__list">
                <li v-for="row in ANTE_TABLE" :key="row.ante" class="ante-row">
                  <span class="ante-row__num">{{ row.ante }}</span>
                  <span class="ante-row__base" :style="{ color: row.color }">
                    <span class="ante-row__chip"></span>
                    {{ row.base }}
                  </span>
                </li>
              </ul>
            </aside>

            <!-- Contenedor principal de los Blinds -->
            <div class="blinds-layout">
              <section v-if="!filters.type || filters.type === 'all'" class="blinds-hero">
                <header class="mod-section__head" style="color: #cfd6d8">
                  ANTE
                  <span class="mod-section__count">{{ heroBlinds.length }}</span>
                </header>
                <div v-if="heroBlinds.length" class="blinds-hero__row">
                  <BlindCard
                    v-for="blind in heroBlinds"
                    :key="`hero-${blind.id}`"
                    :item="blind"
                    variant="hero"
                    :is-selected="selectedItem?.id === blind.id && selectedItem?._kind === 'blind'"
                    @select="onSelect($event, 'blind')"
                    @hover="onHoverBlind"
                    @leave="onLeave"
                  />
                </div>
                <p v-else class="mod-section__empty">— no items —</p>
              </section>

              <section
                v-if="!filters.type || filters.type === 'all' || filters.type === 'BOSS'"
                class="mod-section"
              >
                <header class="mod-section__head" style="color: #e84040">
                  BOSS BLINDS
                  <span class="mod-section__count">{{ normalBossBlinds.length }}</span>
                </header>
                <div
                  v-if="normalBossBlinds.length"
                  class="grid mod-section__grid blinds-grid"
                  :style="{
                    gridTemplateColumns: `repeat(${effectiveBlindCols}, 1fr)`,
                    gap: '12px',
                  }"
                >
                  <BlindCard
                    v-for="blind in normalBossBlinds"
                    :key="`boss-${blind.id}`"
                    :item="blind"
                    variant="grid"
                    :is-selected="selectedItem?.id === blind.id && selectedItem?._kind === 'blind'"
                    @select="onSelect($event, 'blind')"
                    @hover="onHoverBlind"
                    @leave="onLeave"
                  />
                </div>
                <p v-else class="mod-section__empty">— no items —</p>
              </section>

              <section
                v-if="!filters.type || filters.type === 'all' || filters.type === 'FINISHER'"
                class="mod-section"
              >
                <header class="mod-section__head" style="color: #f0a020">
                  FINISHER BLINDS
                  <span class="mod-section__count">{{ finisherBossBlinds.length }}</span>
                </header>
                <div
                  v-if="finisherBossBlinds.length"
                  class="grid mod-section__grid blinds-grid"
                  :style="{
                    gridTemplateColumns: `repeat(${effectiveBlindCols}, 1fr)`,
                    gap: '12px',
                  }"
                >
                  <BlindCard
                    v-for="blind in finisherBossBlinds"
                    :key="`finisher-${blind.id}`"
                    :item="blind"
                    variant="grid"
                    :is-selected="selectedItem?.id === blind.id && selectedItem?._kind === 'blind'"
                    @select="onSelect($event, 'blind')"
                    @hover="onHoverBlind"
                    @leave="onLeave"
                  />
                </div>
                <p v-else class="mod-section__empty">— no items —</p>
              </section>
            </div>
          </div>

          <!-- ============ TAGS ============ -->
          <div v-else-if="!loading && !error && currentSub === 'tags'" class="section--tags">
            <div
              v-if="filteredTags.length"
              class="grid tags-grid"
              :style="{ gridTemplateColumns: `repeat(${effectiveTagCols}, 1fr)`, gap: '12px' }"
            >
              <TagCard
                v-for="tag in filteredTags"
                :key="tag.id"
                :item="tag"
                :is-selected="selectedItem?.id === tag.id && selectedItem?._kind === 'tag'"
                @select="onSelect($event, 'tag')"
                @hover="onHoverTag"
                @leave="onLeave"
              />
            </div>
            <p v-else class="mod-section__empty">— no items —</p>
          </div>
        </div>
      </div>

      <!-- Backdrop del bottom sheet (solo se ve cuando está abierto en móvil/tablet) -->
      <div v-if="detailSheetOpen" class="detail-backdrop" @click="closeDetailSheet" />

      <!-- Columna derecha / Bottom sheet -->
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
          <ItemDetailPanel
            :item="selectedItem"
            :is-locked="selectedItem ? isLocked(selectedItem) : false"
            :can-unlock="true"
            @manual-unlock="onManualUnlock"
            @stake-updated="onStakeUpdated"
          />
        </div>
      </div>
    </div>

    <!-- Tooltip flotante: comparte componente para unlockable/blind/tag -->
    <ItemTooltip
      v-if="tooltip"
      :item="tooltip.item"
      :is-locked="tooltip.kind === 'unlockable' && isLocked(tooltip.item)"
      :card-center-x="tooltip.cardCenterX"
      :card-top="tooltip.cardTop"
      :kind="tooltip.kind"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores/auth";
import { useBackgroundStore } from "@/stores/background";
import {
  fetchAllDecks,
  fetchAllVouchers,
  fetchAllBoosterPacks,
  fetchAllChallengeDecks,
  fetchAllCardModifiers,
  unlockItem,
  relockItem,
} from "@/services/collection";
import { fetchAllBlinds, fetchAllTags } from "@/services/reference";
import { fetchAllJokers } from "@/services/jokers";
import { fetchAllConsumables } from "@/services/consumables";
import { isItemLocked } from "@/constants/items";
import { useProgressionStore } from "@/stores/progression";
import { useHideHeaderOnScroll } from "@/composables/useHideHeaderOnScroll";
import { useViewport } from "@/composables/useViewport";
import { useDictionaryStore } from "@/stores/dictionary";
import { setStickerApplication } from "@/services/progression";

import FilterBar from "@/components/common/FilterBar.vue";
import ProgressBar from "@/components/common/ProgressBar.vue";
import ItemCard from "@/components/items/ItemCard.vue";
import ItemDetailPanel from "@/components/items/ItemDetailPanel.vue";
import ItemTooltip from "@/components/items/ItemTooltip.vue";
import BlindCard from "@/components/items/BlindCard.vue";
import TagCard from "@/components/items/TagCard.vue";

const authStore = useAuthStore();
const { isAuthenticated, lastSyncedAt } = storeToRefs(authStore);
const bgStore = useBackgroundStore();

const progStore = useProgressionStore();

// Ref al contenedor scrollable → composable que oculta AppHeader en móvil.
const scrollEl = ref(null);
useHideHeaderOnScroll(scrollEl);

// Viewport reactivo → sincroniza el nº de columnas visuales con los
// props col-index/col-count que se le pasan a ItemCard. Sin esto, el
// arco por fila se rompe en móvil (la grid pinta 4 cols pero las cartas
// rotan como si fueran 6/8/etc).
const { isMobile, isTablet } = useViewport();
function colsByViewport(desktop, tablet, mobile) {
  if (isMobile.value) return mobile;
  if (isTablet.value) return tablet;
  return desktop;
}

const SUBTABS = [
  { id: "decks", label: "DECKS", color: "#e84040" },
  { id: "booster-packs", label: "PACKS", color: "#f59e0b" },
  { id: "vouchers", label: "VOUCHERS", color: "#3b82f6" },
  { id: "card-modifiers", label: "MODIFIERS", color: "#22c55e" },
  { id: "blinds", label: "BLINDS", color: "#cf3535" },
  { id: "tags", label: "TAGS", color: "#22c55e" },
];

const DECK_COLS = 6;
const PACK_COLS = 3;
const VOUCHER_COLS = 6;
const MOD_COLS = 8;
const BLIND_COLS = 5;
const TAG_COLS = 6;

// Cols efectivas por subtab. Las constantes originales son el valor
// "desktop"; en tablet/móvil bajamos para que las cartas no queden
// microscópicas. Cualquier ajuste de aquí se refleja AUTOMATICAMENTE
// en el inline-style del grid y en los props col-index/col-count.
const effectiveDeckCols = computed(() => colsByViewport(DECK_COLS, 5, 4));
const effectivePackCols = computed(() => colsByViewport(PACK_COLS, 3, 3));
const effectiveVoucherCols = computed(() => colsByViewport(VOUCHER_COLS, 5, 4));
const effectiveModCols = computed(() => colsByViewport(MOD_COLS, 6, 4));
const effectiveBlindCols = computed(() => colsByViewport(BLIND_COLS, 4, 3));
const effectiveTagCols = computed(() => colsByViewport(TAG_COLS, 5, 4));

const PACK_TYPES = [
  { id: "ARCANA", label: "ARCANA", color: "#D8B062" },
  { id: "CELESTIAL", label: "CELESTIAL", color: "#4790A1" },
  { id: "STANDARD", label: "STANDARD", color: "#cf3535" },
  { id: "BUFFOON", label: "BUFFOON", color: "#8b5cf6" },
  { id: "SPECTRAL", label: "SPECTRAL", color: "#5066A5" },
];
const PACK_SIZE_ORDER = { NORMAL: 0, JUMBO: 1, MEGA: 2 };

const MOD_SECTIONS = [
  { key: "enhancements", label: "ENHANCEMENTS", color: "#22c55e" },
  { key: "editions", label: "EDITIONS", color: "#a855f7" },
  { key: "seals", label: "SEALS", color: "#f59e0b" },
];

const ANTE_TABLE = [
  { ante: 1, base: "300", color: "#e84040" },
  { ante: 2, base: "800", color: "#e84040" },
  { ante: 3, base: "2,000", color: "#e84040" },
  { ante: 4, base: "5,000", color: "#e84040" },
  { ante: 5, base: "11,000", color: "#e84040" },
  { ante: 6, base: "20,000", color: "#e84040" },
  { ante: 7, base: "35,000", color: "#e84040" },
  { ante: 8, base: "50,000", color: "#e84040" },
  { ante: 9, base: "110,000", color: "#e84040" },
  { ante: 10, base: "560,000", color: "#e84040" },
  { ante: 11, base: "7,200,000", color: "#e84040" },
  { ante: 12, base: "300,000,000", color: "#e84040" },
  { ante: 13, base: "47,000,000,000", color: "#a8c4c8" },
  { ante: 14, base: "2.900e13", color: "#a8c4c8" },
  { ante: 15, base: "7.700e16", color: "#a8c4c8" },
  { ante: 16, base: "8.600e20", color: "#a8c4c8" },
];

// ── Estado ────────────────────────────────────────────────────────
import BalatroLoader from "@/components/common/BalatroLoader.vue";

const currentSub = ref("decks");
const loading = ref(false);
const showLoader = ref(true);
const error = ref("");

const detailSheetOpen = ref(false);

const decks = ref([]);
const vouchers = ref([]);
const boosterPacks = ref([]);
const challengeDecks = ref([]);
const modifiers = ref({ enhancements: [], editions: [], seals: [] });
const blinds = ref([]);
const tags = ref([]);

const currentSubLabel = computed(() => SUBTABS.find((s) => s.id === currentSub.value)?.label || "");

/**
 * Sub-tabs sin detail-col (full-width grid). BLINDS y TAGS muestran
 * info solo en tooltip flotante; sus tarjetas no se "seleccionan".
 */
const isFullWidth = computed(() => currentSub.value === "blinds" || currentSub.value === "tags");

function defaultFilters() {
  return { search: "", sort: "id", status: "all", type: "all", size: "all" };
}

function selectSub(id) {
  if (currentSub.value === id) return;
  currentSub.value = id;
  selectedItem.value = null;
  tooltip.value = null;
  filters.value = defaultFilters(id);
  bgStore.setPreset(id);
}

// ── Carga ─────────────────────────────────────────────────────────
/**
 * Cargamos los sub-tabs en SECUENCIA, no en paralelo (max_user_connections=5).
 * Coste: ~600-800 ms total en la primera carga; aceptable.
 */
async function loadAll() {
  loading.value = true;
  showLoader.value = true;
  error.value = "";
  try {
    decks.value = await fetchAllDecks({ authenticated: isAuthenticated.value });
    vouchers.value = await fetchAllVouchers({ authenticated: isAuthenticated.value });
    boosterPacks.value = await fetchAllBoosterPacks({ authenticated: isAuthenticated.value });
    challengeDecks.value = await fetchAllChallengeDecks({
      authenticated: isAuthenticated.value,
    });
    modifiers.value = await fetchAllCardModifiers();
    blinds.value = await fetchAllBlinds();
    tags.value = await fetchAllTags();

    // Fetch silencioso en background alimentando el diccionario
    const dictStore = useDictionaryStore();
    dictStore.registerItems(blinds.value);
    dictStore.registerItems(tags.value);
    fetchAllJokers()
      .then((items) => dictStore.registerItems(items))
      .catch(() => {});
    fetchAllConsumables()
      .then((items) => dictStore.registerItems(items))
      .catch(() => {});
  } catch (e) {
    console.error("[CollectionView] error completo:", e, e.cause || "");
    error.value = e.message || "Unknown error loading collection.";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  bgStore.setPreset(currentSub.value);
  progStore.init();
  loadAll();
});

watch(isAuthenticated, loadAll);
watch(lastSyncedAt, loadAll);

// ── Lock state ───────────────────────────────────────────────────
function isLocked(item) {
  if (String(item?.type || "").toUpperCase() === "CHALLENGE_DECK") {
    const defaultUnlocked = [
      "THE OMELETTE",
      "15 MINUTE CITY",
      "RICH GET RICHER",
      "ON A KNIFE'S EDGE",
      "X-RAY VISION",
    ];
    if (defaultUnlocked.includes(String(item.name || "").toUpperCase())) {
      return false; // Siempre desbloqueados
    }
  }
  return isItemLocked(item, isAuthenticated.value);
}

// ── Filtros por sub-tab ──────────────────────────────────────────
const filters = ref(defaultFilters());

const enabledFilters = computed(() => {
  const base = (() => {
    switch (currentSub.value) {
      case "decks":
        return ["search", "status", "sort", "type"];
      case "booster-packs":
        return ["search", "type", "size"];
      case "vouchers":
        return ["search", "status", "type"];
      case "card-modifiers":
        return ["search", "type"];
      case "blinds":
        return ["search", "type"];
      case "tags":
        return ["search"];
      default:
        return ["search", "sort"];
    }
  })();
  if (!isAuthenticated.value) {
    return base.filter((f) => f !== "status");
  }
  return base;
});

const sizeOptions = computed(() => {
  if (currentSub.value === "booster-packs") {
    return [
      { value: "all", label: "Size: All" },
      { value: "NORMAL", label: "Normal" },
      { value: "JUMBO", label: "Jumbo" },
      { value: "MEGA", label: "Mega" },
    ];
  }
  return [];
});

const typeOptions = computed(() => {
  if (currentSub.value === "decks") {
    return [
      { value: "all", label: "Type: All" },
      { value: "normal", label: "Normal" },
      { value: "challenge", label: "Challenge" },
    ];
  }
  if (currentSub.value === "booster-packs") {
    return [
      { value: "all", label: "Type: All" },
      { value: "ARCANA", label: "Arcana" },
      { value: "CELESTIAL", label: "Celestial" },
      { value: "STANDARD", label: "Standard" },
      { value: "BUFFOON", label: "Buffoon" },
      { value: "SPECTRAL", label: "Spectral" },
    ];
  }
  if (currentSub.value === "vouchers") {
    return [
      { value: "all", label: "Type: All" },
      { value: "BASE", label: "Base" },
      { value: "UPGRADED", label: "Upgraded" },
    ];
  }
  if (currentSub.value === "card-modifiers") {
    return [
      { value: "all", label: "Type: All" },
      { value: "enhancements", label: "Enhancements" },
      { value: "editions", label: "Editions" },
      { value: "seals", label: "Seals" },
    ];
  }
  if (currentSub.value === "blinds") {
    return [
      { value: "all", label: "Type: All" },
      { value: "BOSS", label: "Boss" },
      { value: "FINISHER", label: "Finisher" },
    ];
  }
  return [];
});

// ── Filtros (helpers compartidos) ────────────────────────────────
function statusMatches(item) {
  if (filters.value.status === "unlocked") return !isLocked(item);
  if (filters.value.status === "locked") return isLocked(item);
  return true;
}

function sortItems(arr) {
  return [...arr].sort((a, b) => {
    if (filters.value.sort === "name") return (a.name || "").localeCompare(b.name || "");
    const oa = a.item_number ?? a.id;
    const ob = b.item_number ?? b.id;
    return oa - ob;
  });
}

function applyBaseFilters(arr) {
  const search = filters.value.search.toLowerCase();
  return arr.filter((it) => {
    if (search) {
      const match =
        (it.name || "").toLowerCase().includes(search) ||
        (it.description || it.effect || "").toLowerCase().includes(search);
      if (!match) return false;
    }
    return true;
  });
}

// ── Decks regulares ───────────────────────────────────────────────
const filteredDecks = computed(() => {
  if (filters.value.type === "challenge") return [];
  let list = applyBaseFilters(decks.value);
  list = list.filter(statusMatches);
  return sortItems(list);
});

// ── Challenge Decks ───────────────────────────────────────────────
const filteredChallengeDecks = computed(() => {
  if (filters.value.type === "normal") return [];
  let list = applyBaseFilters(challengeDecks.value);
  list = list.filter(statusMatches);
  return sortItems(list);
});

// ── Vouchers ─────────────────────────────────────────────────────
const filteredVouchers = computed(() => {
  let list = applyBaseFilters(vouchers.value);
  list = list.filter(statusMatches);
  if (filters.value.type === "BASE") {
    list = list.filter((v) => String(v.voucher_tier).toUpperCase() === "BASE");
  } else if (filters.value.type === "UPGRADED") {
    list = list.filter((v) => String(v.voucher_tier).toUpperCase() === "UPGRADED");
  }
  return [...list].sort((a, b) => (a.name || "").localeCompare(b.name || ""));
});

// ── Booster Packs ────────────────────────────────────────────────
const groupedBoosterPacks = computed(() => {
  let list = applyBaseFilters(boosterPacks.value);
  list = list.filter(statusMatches);

  // Filtrar por tamaño de sobre
  if (filters.value.size && filters.value.size !== "all") {
    list = list.filter((p) => String(p.size).toUpperCase() === filters.value.size);
  }

  // Filtramos qué SECCIONES mostrar según el desplegable
  const activeTypes = PACK_TYPES.filter((t) => {
    if (!filters.value.type || filters.value.type === "all") return true;
    return String(t.id).toUpperCase() === filters.value.type;
  });

  return activeTypes.map((t) => {
    const items = list
      .filter((p) => String(p.pack_type).toUpperCase() === t.id)
      .sort((a, b) => {
        const oa = PACK_SIZE_ORDER[a.size] ?? 99;
        const ob = PACK_SIZE_ORDER[b.size] ?? 99;
        if (oa !== ob) return oa - ob;
        return (a.item_number ?? a.id) - (b.item_number ?? b.id);
      });
    return { packType: t.id, label: t.label, color: t.color, items };
  });
});

function enrichedPackName(pack) {
  const sized = pack.size ? `${pack.name} ${pack.size}` : pack.name;
  return { ...pack, name: sized };
}

const packRows = computed(() => {
  const groups = groupedBoosterPacks.value;
  const rows = [];
  for (let i = 0; i < groups.length; i += 2) {
    rows.push(groups.slice(i, i + 2));
  }
  return rows;
});

// ── Card Modifiers ───────────────────────────────────────────────
const filteredModifierGroups = computed(() => {
  return MOD_SECTIONS.filter((sec) => {
    if (filters.value.type === "all") return true;
    return sec.key === filters.value.type;
  }).map((sec) => {
    let list = applyBaseFilters(modifiers.value[sec.key] || []);
    list = sortItems(list);
    return { ...sec, items: list };
  });
});

// ── Blinds ───────────────────────────────────────────────────────
/**
 * Search aplicable a blinds (busca en name + description).
 */
function applyBlindSearch(arr) {
  const search = filters.value.search.toLowerCase();
  return arr.filter((b) => {
    if (search) {
      const match =
        (b.name || "").toLowerCase().includes(search) ||
        (b.description || "").toLowerCase().includes(search);
      if (!match) return false;
    }
    return true;
  });
}

/**
 * Filtro de tipo para BLINDS:
 *   - 'all': todos los tipos (sin filtro).
 *   - 'BOSS': solo BOSS no-finisher (ante != "8").
 *   - 'FINISHER': solo BOSS con ante == "8".
 * Small y Big siempre se muestran si el filtro es 'all' (caen como
 * hero tiles aparte) o se filtran fuera si el tipo es BOSS/FINISHER.
 */
function applyBlindTypeFilter(arr, type) {
  if (!type || type === "all") return arr;
  if (type === "BOSS") {
    return arr.filter((b) => String(b.blind_type || "").toUpperCase() === "BOSS");
  }
  if (type === "FINISHER") {
    return arr.filter((b) => String(b.blind_type || "").toUpperCase() === "SHOWDOWN");
  }
  return arr;
}

/**
 * Hero blinds: Small + Big (los únicos blinds no-Boss). El filtro de
 * tipo BOSS/FINISHER los esconde — coherente con que el usuario está
 * buscando uno de los Boss específicos en ese caso.
 */
const heroBlinds = computed(() => {
  const filtered = applyBlindSearch(blinds.value);
  if (filters.value.type === "BOSS" || filters.value.type === "FINISHER") return [];
  return filtered
    .filter((b) => {
      const t = String(b.blind_type || "").toUpperCase();
      return t === "SMALL" || t === "BIG";
    })
    .sort((a, b) => {
      // SMALL antes que BIG. El score_multiplier ordena correctamente
      // (Small=1, Big=1.5) pero por si los datos cambian, fallback
      // alfabético.
      const oa = a.score_multiplier ?? 0;
      const ob = b.score_multiplier ?? 0;
      return oa - ob;
    });
});

const normalBossBlinds = computed(() => {
  const filtered = applyBlindSearch(blinds.value);
  const typed = applyBlindTypeFilter(filtered, filters.value.type);
  return typed
    .filter((b) => String(b.blind_type || "").toUpperCase() === "BOSS")
    .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
});

const finisherBossBlinds = computed(() => {
  const filtered = applyBlindSearch(blinds.value);
  const typed = applyBlindTypeFilter(filtered, filters.value.type);
  return typed
    .filter((b) => String(b.blind_type || "").toUpperCase() === "SHOWDOWN")
    .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
});

// ── Tags ─────────────────────────────────────────────────────────
const filteredTags = computed(() => {
  const search = filters.value.search.toLowerCase();
  return tags.value
    .filter((t) => {
      if (search) {
        const match =
          (t.name || "").toLowerCase().includes(search) ||
          (t.description || "").toLowerCase().includes(search);
        if (!match) return false;
      }
      return true;
    })
    .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
});

// ── Counters ─────────────────────────────────────────────────────
const subtabCount = computed(() => {
  if (currentSub.value === "decks")
    return filteredDecks.value.length + filteredChallengeDecks.value.length;
  if (currentSub.value === "vouchers") return filteredVouchers.value.length;
  if (currentSub.value === "booster-packs")
    return groupedBoosterPacks.value.reduce((acc, g) => acc + g.items.length, 0);
  if (currentSub.value === "card-modifiers")
    return filteredModifierGroups.value.reduce((acc, g) => acc + g.items.length, 0);
  if (currentSub.value === "blinds")
    return (
      heroBlinds.value.length + normalBossBlinds.value.length + finisherBossBlinds.value.length
    );
  if (currentSub.value === "tags") return filteredTags.value.length;
  return 0;
});

/**
 * Total y desbloqueados a través de TODOS los sub-tabs — para la
 * ProgressBar global. BLINDS y TAGS cuentan como "siempre desbloqueados"
 * porque no son Unlockables y queremos que la % refleje la presencia
 * completa de información en la app.
 */
const allUnlockableItems = computed(() => [
  ...decks.value,
  ...vouchers.value,
  ...boosterPacks.value,
  ...(modifiers.value.enhancements || []),
  ...(modifiers.value.editions || []),
  ...(modifiers.value.seals || []),
]);

const globalTotal = computed(
  () => allUnlockableItems.value.length + blinds.value.length + tags.value.length,
);

const globalUnlocked = computed(() => {
  // Unlockables reales: los que no están locked según isItemLocked
  const realUnlocked = allUnlockableItems.value.filter((it) => !isLocked(it)).length;
  // Blinds y Tags suman su total entero (siempre desbloqueados)
  const referenceUnlocked = blinds.value.length + tags.value.length;
  return realUnlocked + referenceUnlocked;
});

// ── Selección + tooltip ──────────────────────────────────────────
const selectedItem = ref(null);
const tooltip = ref(null);
let hoverTimer = null;

function onSelect(item, kind, modKey = null) {
  // Toggle protection
  if (
    selectedItem.value &&
    selectedItem.value.id === item.id &&
    selectedItem.value._kind === kind
  ) {
    return;
  }

  const enriched = { ...item, _kind: kind, _modKey: modKey };

  if (kind === "voucher" && item.next_voucher_id) {
    const upgrade = vouchers.value.find((v) => v.id === item.next_voucher_id);
    if (upgrade) {
      enriched._nextVoucher = { id: upgrade.id, name: upgrade.name, image_url: upgrade.image_url };
    }
  }
  selectedItem.value = enriched;

  // En desktop el panel ya está visible; abrir el sheet solo cambia
  // estado interno que el CSS aplica solo en tablet/mobile.
  detailSheetOpen.value = true;
}

function closeDetailSheet() {
  detailSheetOpen.value = false;
  // No desmarcamos selectedJoker — al cerrar y reabrir mantiene la carta
  // selecciondaa visible en el panel.
}

/**
 * Desbloqueo/Re-bloqueo manual desde el detail panel.
 *
 * El ItemDetailPanel emite (item, unlocked); elegimos servicio.
 * Mutamos localmente — preserva animación y scroll. Para
 * challenge_deck escribimos al array correspondiente.
 */
async function onManualUnlock(item, unlocked = true) {
  if (!item) return;
  try {
    if (unlocked) {
      await unlockItem(item.id);
      mutateLocally(item, { unlocked_for_me: true, unlocked_at: new Date().toISOString() });
    } else {
      await relockItem(item.id);
      mutateLocally(item, { unlocked_for_me: false, unlocked_at: null });
    }
  } catch (e) {
    console.error("[CollectionView] toggle unlock failed", e);
    if (e?.response?.status === 401) {
      authStore.openAuthModal();
      return;
    }
    const verb = unlocked ? "mark as unlocked" : "lock again";
    alert(`Could not ${verb}. ` + (e.message || ""));
  }
}

async function onStakeUpdated(data) {
  let targetArray;
  if (currentSub.value === "decks") {
    if (selectedItem.value?._kind === "challenge_deck") {
      targetArray = challengeDecks.value;
    } else {
      targetArray = decks.value;
    }
  } else {
    return;
  }

  const item = targetArray.find((i) => i.id === data.id);

  if (item) {
    const oldStake = item.highest_stake_order || 0;
    // Forzamos que los null/undefined se conviertan matemáticamente en 0
    const newStake = data.highest_stake_order || 0;
    item.highest_stake_order = newStake;

    if (selectedItem.value?._kind === "challenge_deck") {
      const challenges = [...challengeDecks.value].sort(
        (a, b) => (a.item_number ?? a.id) - (b.item_number ?? b.id),
      );

      if (newStake === 1 && oldStake === 0) {
        // Desbloquear el siguiente
        const nextLocked = challenges.find((c) => isLocked(c));
        if (nextLocked) {
          await unlockItem(nextLocked.id);
          mutateLocally(nextLocked, {
            unlocked_for_me: true,
            unlocked_at: new Date().toISOString(),
          });
        }
      } else if (newStake === 0 && oldStake === 1) {
        // Bloquear el último
        const unlockedChallenges = challenges.filter((c) => !isLocked(c));

        if (unlockedChallenges.length > 5) {
          const lastUnlocked = unlockedChallenges[unlockedChallenges.length - 1];

          if (lastUnlocked.highest_stake_order === 1) {
            try {
              await setStickerApplication(lastUnlocked.id, 0);
              lastUnlocked.highest_stake_order = 0;
            } catch (e) {
              console.error("Failed to uncomplete the cascaded challenge", e);
            }
          }

          await relockItem(lastUnlocked.id);
          mutateLocally(lastUnlocked, { unlocked_for_me: false, unlocked_at: null });
        }
      }
    }
  }

  // Comprobación de seguridad
  if (selectedItem.value && selectedItem.value.id === data.id) {
    selectedItem.value.highest_stake_order = data.highest_stake_order || 0;
  }
}

function mutateLocally(item, patch) {
  const kind = selectedItem.value?._kind;
  let arr = null;
  if (kind === "deck") arr = decks.value;
  else if (kind === "voucher") arr = vouchers.value;
  else if (kind === "pack") arr = boosterPacks.value;
  else if (kind === "challenge_deck") arr = challengeDecks.value;
  if (arr) {
    const target = arr.find((x) => x.id === item.id);
    if (target) Object.assign(target, patch);
  }

  // Solo actualizar selectedItem si es EXACTAMENTE la misma carta mutada
  if (selectedItem.value && selectedItem.value.id === item.id) {
    selectedItem.value = { ...selectedItem.value, ...patch };
  }
}

// ── Hover handlers ───────────────────────────────────────────────
/**
 * Tres handlers de hover (uno por kind) para que el tooltip flotante
 * reciba el `kind` correcto. Mismo timing y misma cancelación.
 */
function setTooltipFromHover({ item, target }, kind) {
  clearTimeout(hoverTimer);
  hoverTimer = setTimeout(() => {
    const rect = target.getBoundingClientRect();
    tooltip.value = {
      item,
      kind,
      cardCenterX: rect.left + rect.width / 2,
      cardTop: rect.top,
    };
  }, 120);
}

function onHover(payload) {
  setTooltipFromHover(payload, "unlockable");
}
function onHoverBlind(payload) {
  setTooltipFromHover(payload, "blind");
}
function onHoverTag(payload) {
  setTooltipFromHover(payload, "tag");
}

function onLeave() {
  clearTimeout(hoverTimer);
  tooltip.value = null;
}

onBeforeUnmount(() => clearTimeout(hoverTimer));
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.collection-view {
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

/* Toolbar */
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  align-items: stretch;

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
.subtab--decks {
  background: #3ac58c;
}
.subtab--booster-packs {
  background: #bf8940;
}
.subtab--vouchers {
  background: #5a89a5;
}
.subtab--card-modifiers {
  background: #9f3dc2;
}
.subtab--blinds {
  background: #cf3535;
}
.subtab--tags {
  background: #29d634;
}
.subtab--active {
  filter: brightness(1.25);
}

/* Layout */
.layout {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}
/* Full-width: el grid ocupa todo, sin detail-col en desktop.
 * BLINDS y TAGS no usan ItemDetailPanel en desktop — su info sale por
 * el ItemTooltip flotante. En tablet/mobile el ItemTooltip está
 * oculto y el bottom-sheet vuelve a aparecer (override más abajo en
 * @include tablet). */
.layout--full .grid-col {
  flex: 1;
}
.layout--full .detail-col {
  display: none;
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
  min-height: 0;

  overflow-y: auto;
  overflow-x: hidden;

  display: flex;
  flex-direction: column;

  padding: 28px 22px 32px;
  background: rgba(26, 42, 46, 0.6);

  scrollbar-width: thin;
  scrollbar-color: $panel-mid transparent;

  @include pixel-clip;
}

/* En BLINDS el scroll deja de estar aquí */
.layout--full:has(.blinds-wrapper) .grid-scroll {
  overflow: hidden;
}

.grid {
  display: grid;
  gap: 0;
  row-gap: 16px;
}

/* Booster packs */
.packs-rows {
  display: flex;
  flex-direction: column;
  gap: 28px;
}
.packs-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
}
.packs-row--solo {
  display: flex;
  justify-content: center;
}
.packs-row--solo > .pack-section {
  width: calc(50% - 14px);
}

.pack-section,
.mod-section {
  &__head {
    font-family: "m6x11plus", monospace;
    font-size: 18px;
    letter-spacing: 1.5px;
    margin-bottom: 12px;
    padding: 6px 10px;
    border-left: 4px solid currentColor;
    background: rgba(0, 0, 0, 0.35);
    text-shadow: 0 3px 0 #00000070;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  &__count {
    font-size: 12px;
    color: $text-3;
    margin-left: auto;
  }
  &__empty {
    font-family: "m6x11plus", monospace;
    font-size: 13px;
    color: $text-3;
    text-align: center;
    padding: 12px;
    margin: 0;
  }
}

.sectioned {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

/* ── BLINDS ────────────────────────────────────────────────────── */
/*
 * Layout específico de la subtab BLINDS:
 *   .blinds-hero → fila destacada "apuesta inicial" con Small+Big.
 *   .mod-section → secciones BOSS BLINDS / FINISHER BLINDS reusan el
 *                  estilo de divisiones MEJORAS para coherencia.
 */
.blinds-wrapper {
  flex: 1;
  min-height: 0;

  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 24px;

  align-items: stretch;

  overflow: hidden;
}

.blinds-layout {
  min-width: 0;
  min-height: 0;

  display: flex;
  flex-direction: column;
  gap: 28px;

  overflow-y: auto;
  overflow-x: hidden;

  padding-right: 6px;

  scrollbar-width: thin;
  scrollbar-color: $panel-mid transparent;
}

.blinds-hero {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.blinds-hero__row {
  display: grid;
  /* Hasta 4 tiles para futura expansión (mods); por ahora Small + Big
     → 2 columnas centradas. */
  grid-template-columns: repeat(auto-fit, minmax(180px, 220px));
  justify-content: center;
  gap: 16px;
}

/* Tabla lateral "ANTE / BASE" */
/* Sidebar fijo visualmente */
.ante-sidebar {
  min-height: 0;
  height: 100%;

  background: rgba(0, 0, 0, 0.35);
  padding: 18px 22px;

  display: flex;
  flex-direction: column;

  overflow: hidden;

  @include pixel-clip-sm;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);

  &__head {
    display: flex;
    justify-content: space-between;
    font-family: "m6x11plus", monospace;
    font-size: clamp(16px, 1vw, 20px);
    letter-spacing: 0.5px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid rgba(255, 255, 255, 0.05);
    flex-shrink: 0;
  }

  &__list {
    list-style: none;
    margin: 0;
    padding: 0;

    flex: 1;

    display: flex;
    flex-direction: column;
    justify-content: space-between;

    min-height: 0;
  }
}

.ante-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: 1;
  min-height: 0;
  font-family: "m6x11plus", monospace;
  font-size: clamp(12px, 0.85vw, 16px);
  line-height: 1;

  &__num {
    color: #f0a020;
    font-size: 25px;
  }

  &__base {
    display: flex;
    align-items: center;
    gap: clamp(4px, 0.4vw, 8px);
    letter-spacing: 0.3px;
    font-size: 20px;
  }

  &__chip {
    display: inline-block;
    width: clamp(6px, 0.55vw, 10px);
    height: clamp(6px, 0.55vw, 10px);
    background: #cfd6d8;
    border-radius: 50%;
    box-shadow: inset 0 0 0 2px #2a3a3e;
    opacity: 0.85;
  }
}

/* ── Detail column ─────────────────────────────────────────────── */
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
      font-size: 20px;
    }
  }
  &__body {
    flex: 1;
    overflow: hidden;
  }
}

/* Animaciones de entrada */
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
 * ADAPTACIÓN 1400px — Cuando la pantalla baja de 1400px, no hay
 * espacio para los botones y los filtros en la misma fila.
 * Apilamos el toolbar y hacemos scrollable la lista de subtabs.
 * ────────────────────────────────────────────────────────────── */
@media (max-width: 1450px) {
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
}

/* ──────────────────────────────────────────────────────────────
 * TABLET — el layout pasa a columna única. El panel de detalle se
 * convierte en un bottom sheet que sube cuando hay item seleccionado.
 * El backdrop oscurece el grid mientras el sheet está abierto.
 * ────────────────────────────────────────────────────────────── */
@include tablet {
  .layout {
    flex-direction: column;
  }

  .grid-col {
    width: 100%;
    // FIX (scroll): permite que el .grid-scroll active overflow-y:auto.
    min-height: 0;
  }

  .grid-scroll {
    padding: 18px 14px 24px;
  }

  // Booster packs: stack los pares en lugar de mostrarlos lado a lado.
  .packs-row {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .packs-row--solo > .pack-section {
    width: 100%;
  }

  // BLINDS: ocultamos el sidebar lateral de "ANTE / BASE" — la tabla
  // no aporta valor crítico en móvil/tablet y se solapaba con los
  // blinds del grid principal. El blinds-wrapper pasa a una sola
  // columna ocupada por blinds-layout y los blinds-grid escalan.
  .blinds-wrapper {
    grid-template-columns: 1fr;
    grid-auto-rows: auto;
    gap: 0;
    overflow: visible;
  }
  .ante-sidebar {
    display: none;
  }
  .blinds-layout {
    overflow: visible;
    padding-right: 0;
  }
  // Permitimos que el grid-scroll de blinds use overflow normal para que
  // se sume al scroll del wrapper.
  .layout--full:has(.blinds-wrapper) .grid-scroll {
    overflow-y: auto;
  }

  // Panel detalle → fixed sheet desde abajo.
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

    // FIX (scroll del bottom-sheet): el ItemDetailPanel ahora se puede
    // scrollear dentro del sheet en lugar de quedar recortado.
    &__body {
      overflow-y: auto;
      overflow-x: hidden;
      -webkit-overflow-scrolling: touch;
    }
  }

  // En tablet/mobile el bottom-sheet vuelve a estar disponible
  // INCLUSO para blinds/tags — el ItemTooltip flotante está
  // oculto en estos viewports, así que la info se sirve mediante
  // el panel. El parent debe wirear @select en BlindCard/TagCard.
  .layout--full .detail-col {
    display: flex;
  }

  .detail-backdrop {
    display: block;
  }
}

/* ──────────────────────────────────────────────────────────────
 * Nota: el cap de columnas por viewport YA se aplica desde JS via
 * effectiveXCols (computed con useViewport). Por eso aquí no
 * sobrescribimos grid-template-columns con !important — el inline
 * style ya viene con el valor correcto y matchea el col-count que
 * recibe cada ItemCard, manteniendo el arco por fila intacto.
 * ────────────────────────────────────────────────────────────── */

/* ──────────────────────────────────────────────────────────────
 * MOBILE — pulimos paddings, tipografías y altura del bottom-sheet.
 * Las columnas se manejan via JS (effectiveXCols), no aquí.
 * ────────────────────────────────────────────────────────────── */
@include mobile {
  .grid-scroll {
    padding: 14px 10px 20px;
  }

  // Hero blinds (Small + Big) — apretamos el minmax para que entren
  // ambos a la vez en pantallas estrechas.
  .blinds-hero__row {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
  }

  .count {
    font-size: 14px;
  }

  .subtab {
    font-size: 12px;
    padding: 8px 12px;
  }

  // Sheet ocupa más alto en móvil porque hay menos espacio horizontal.
  .detail-col {
    max-height: 90vh;
  }
}
</style>
