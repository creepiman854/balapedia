<!--
  Vista de COLECCIÓN.

  Pase 2:
    · Carga TODOS los sub-tabs en mount (Promise.all) — necesario para
      calcular la barra de progreso global. Coste: 4 requests
      paralelas al cargar; tras eso, los datos se cachean en refs.
    · Lock state por item (helper isItemLocked): cuando hay sesión y
      el item no es "Available from start", se marca locked salvo que
      el backend devuelva `unlocked_for_me: true`.
    · Sub-tabs reposicionados a la IZQUIERDA del FilterBar (toolbar
      flex). Encima de la toolbar, ProgressBar global cuando hay
      sesión.
    · SOBRES en grid de 2 columnas (ARCANA+CELESTIAL, STANDARD+BUFFOON;
      SPECTRAL solo en su propia fila ocupando todo el ancho).
    · MAZOS recibe `:stack="true"` para mostrar el efecto pila detrás.
    · Filtros por sub-tab:
        DECKS    → search + status + sort
        SOBRES   → search + type (pack) + status + sort
        VALES    → search + sort
        MEJORAS  → search + type (section) + sort
-->
<template>
  <div class="collection-view">
    <div class="layout">
      <!-- ── Columna izquierda ── -->
      <div class="grid-col">
        <!-- Progress bar global (suma de los 4 sub-tabs) -->
        <ProgressBar
          v-if="isAuthenticated && globalTotal > 0"
          :value="globalUnlocked"
          :max="globalTotal"
          color="#22c55e"
          label="COLECCIÓN DESBLOQUEADA"
        />

        <!-- Toolbar: sub-tabs a la izquierda + filtros llenando la fila -->
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
            :sort-options="sortOptions"
            :search-placeholder="`Buscar ${currentSubLabel.toLowerCase()}...`"
          />
        </div>

        <div class="count">
          <template v-if="loading">Cargando colección...</template>
          <template v-else-if="error">{{ error }}</template>
          <template v-else>{{ subtabCount }} elementos</template>
        </div>

        <div class="grid-scroll">
          <!-- ============ MAZOS ============ -->
          <div
            v-if="!loading && !error && currentSub === 'decks'"
            class="grid"
            :style="{ gridTemplateColumns: `repeat(${DECK_COLS}, 1fr)` }"
          >
            <ItemCard
              v-for="(item, idx) in filteredDecks"
              :key="item.id"
              class="card-deal-anim"
              :style="{ animationDelay: `${Math.min(idx, 50) * 35}ms` }"
              :item="item"
              :is-locked="isLocked(item)"
              :is-selected="selectedItem?.id === item.id && selectedItem?._kind === 'deck'"
              :col-index="idx % DECK_COLS"
              :col-count="DECK_COLS"
              :stack="true"
              @select="onSelect($event, 'deck')"
              @hover="onHover"
              @leave="onLeave"
            />
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
                  class="grid pack-section__grid"
                  :style="{ gridTemplateColumns: `repeat(${PACK_COLS}, 1fr)` }"
                >
                  <ItemCard
                    v-for="(pack, idx) in group.items"
                    :key="pack.id"
                    class="card-deal-anim"
                    :style="{ animationDelay: `${Math.min(idx, 50) * 35}ms` }"
                    :item="enrichedPackName(pack)"
                    :is-locked="isLocked(pack)"
                    :is-selected="selectedItem?.id === pack.id && selectedItem?._kind === 'pack'"
                    :col-index="idx % PACK_COLS"
                    :col-count="PACK_COLS"
                    @select="onSelect($event, 'pack')"
                    @hover="onHover"
                    @leave="onLeave"
                  />
                </div>
              </section>
            </div>
          </div>

          <!-- ============ VALES (vouchers) ============ -->
          <div
            v-else-if="!loading && !error && currentSub === 'vouchers'"
            class="grid"
            :style="{ gridTemplateColumns: `repeat(${VOUCHER_COLS}, 1fr)` }"
          >
            <ItemCard
              v-for="(item, idx) in filteredVouchers"
              :key="item.id"
              class="card-deal-anim"
              :style="{ animationDelay: `${Math.min(idx, 50) * 35}ms` }"
              :item="item"
              :is-locked="isLocked(item)"
              :is-selected="selectedItem?.id === item.id && selectedItem?._kind === 'voucher'"
              :col-index="idx % VOUCHER_COLS"
              :col-count="VOUCHER_COLS"
              @select="onSelect($event, 'voucher')"
              @hover="onHover"
              @leave="onLeave"
            />
          </div>

          <!-- ============ MEJORAS (card modifiers) ============ -->
          <div v-else-if="!loading && !error && currentSub === 'card-modifiers'" class="sectioned">
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
                :style="{ gridTemplateColumns: `repeat(${MOD_COLS}, 1fr)` }"
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
                  :col-index="idx % MOD_COLS"
                  :col-count="MOD_COLS"
                  @select="onSelect($event, 'modifier', modGroup.key)"
                  @hover="onHover"
                  @leave="onLeave"
                />
              </div>
              <p v-else class="mod-section__empty">— sin elementos —</p>
            </section>
          </div>
        </div>
      </div>

      <!-- ── Columna derecha ── -->
      <div class="detail-col">
        <div class="detail-col__head">
          <span>{{
            selectedItem ? selectedItem.name.toUpperCase() : currentSubLabel.toUpperCase()
          }}</span>
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

    <ItemTooltip
      v-if="tooltip"
      :item="tooltip.item"
      :is-locked="isLocked(tooltip.item)"
      :card-center-x="tooltip.cardCenterX"
      :card-top="tooltip.cardTop"
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
  fetchAllCardModifiers,
  unlockItem,
} from "@/services/collection";
import { isItemLocked } from "@/constants/items";
import { useProgressionStore } from "@/stores/progression";

import FilterBar from "@/components/common/FilterBar.vue";
import ProgressBar from "@/components/common/ProgressBar.vue";
import ItemCard from "@/components/items/ItemCard.vue";
import ItemDetailPanel from "@/components/items/ItemDetailPanel.vue";
import ItemTooltip from "@/components/items/ItemTooltip.vue";

const authStore = useAuthStore();
const { isAuthenticated, lastSyncedAt } = storeToRefs(authStore);
const bgStore = useBackgroundStore();

const progStore = useProgressionStore();

const SUBTABS = [
  { id: "decks", label: "MAZOS", color: "#e84040" },
  { id: "booster-packs", label: "SOBRES", color: "#f59e0b" },
  { id: "vouchers", label: "VALES", color: "#3b82f6" },
  { id: "card-modifiers", label: "MEJORAS", color: "#22c55e" },
];

const DECK_COLS = 6;
const PACK_COLS = 3; // dentro de cada grupo pack_type
const VOUCHER_COLS = 6;
const MOD_COLS = 8;

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

// ── Estado ────────────────────────────────────────────────────────
const currentSub = ref("decks");
const loading = ref(false);
const error = ref("");

const decks = ref([]);
const vouchers = ref([]);
const boosterPacks = ref([]);
const modifiers = ref({ enhancements: [], editions: [], seals: [] });

const currentSubLabel = computed(() => SUBTABS.find((s) => s.id === currentSub.value)?.label || "");

function defaultFilters(sub = currentSub.value) {
  // Vouchers arrancan en 'name' (A-Z) porque su sortOptions no
  // incluye 'id'. El resto usa 'id' como sort por defecto.
  const defaultSort = sub === "vouchers" ? "name" : "id";
  return { search: "", sort: defaultSort, status: "all", type: "all" };
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
 * Cargamos los 4 sub-tabs en SECUENCIA, no en paralelo.
 *
 * Por qué: el plan de hosting actual del backend permite solo 5
 * conexiones simultáneas por usuario MySQL (max_user_connections=5).
 * Promise.all con 4 sub-tabs disparaba 4 conexiones a la vez; si el
 * usuario tenía otras pestañas/requests abiertas (auth, /api/me/*),
 * se llegaba a 5+ y MySQL devolvía 1226 → el backend respondía 500.
 *
 * Secuencial cierra cada conexión antes de abrir la siguiente, así
 * nunca hay más de 1 conexión activa de esta vista a la vez. Coste:
 * ~400-600 ms más en la primera carga, una sola vez.
 */
async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    decks.value = await fetchAllDecks({ authenticated: isAuthenticated.value });
    // Vouchers también necesita el endpoint autenticado para que la
    // cascade del Steam sync (BAL_07 → Nacho Tong, BAL_08 → Recyclomancy)
    // sea visible en la UI. Sin esto, el cascade SÍ crea las filas
    // UserUnlock pero el frontend lee del endpoint público sin overlay
    // y los vouchers parecen siempre locked.
    vouchers.value = await fetchAllVouchers({ authenticated: isAuthenticated.value });
    // Booster packs también van por el endpoint autenticado para
    // mantener la simetría con jokers/decks/vouchers. En vanilla
    // Balatro no cambia nada (no hay sobres con unlock_factor), pero
    // si en el futuro un mod añade sobres desbloqueables, ya
    // funciona sin tocar más código.
    boosterPacks.value = await fetchAllBoosterPacks({ authenticated: isAuthenticated.value });
    modifiers.value = await fetchAllCardModifiers();
  } catch (e) {
    console.error("[CollectionView] error completo:", e, e.cause || "");
    error.value = e.message || "Error desconocido al cargar la colección.";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  bgStore.setPreset(currentSub.value);
  progStore.init();
  loadAll();
});

// Si la sesión cambia, recargamos para que decks/vouchers recojan el
// overlay (/api/me/decks, /api/me/vouchers) y los demás se reajusten
// al nuevo lock state.
watch(isAuthenticated, loadAll);

// Si el authStore notifica un sync de Steam (sync exitoso O unlink),
// recargamos para reflejar los nuevos unlocks o el re-lock de items
// que vinieron de STEAM_SYNC. Es el mecanismo simétrico al que ya
// usan JokersView y AchievementsView.
watch(lastSyncedAt, loadAll);

// ── Lock state ───────────────────────────────────────────────────
function isLocked(item) {
  return isItemLocked(item, isAuthenticated.value);
}

// ── Filtros por sub-tab ──────────────────────────────────────────
const filters = ref(defaultFilters());

const enabledFilters = computed(() => {
  // Filtros base por sub-tab.
  //   SOBRES y MEJORAS: solo type (sort no aporta — ya vienen
  //   alfabéticos del backend y agrupados visualmente).
  //   VALES: status + sort (con sort options custom — ver
  //   sortOptions abajo).
  const base = (() => {
    switch (currentSub.value) {
      case "decks":
        return ["search", "status", "sort"];
      case "booster-packs":
        return ["search", "type"];
      case "vouchers":
        return ["search", "status", "sort"];
      case "card-modifiers":
        return ["search", "type"];
      default:
        return ["search", "sort"];
    }
  })();
  // El filtro 'status' (unlocked/locked) no tiene sentido sin sesión
  // — todo se ve. Lo eliminamos del array para que ni siquiera
  // aparezca el select.
  if (!isAuthenticated.value) {
    return base.filter((f) => f !== "status");
  }
  return base;
});

/**
 * Opciones del select de ORDEN por sub-tab.
 *   VALES: A-Z (default) / BASE / UPGRADED.
 *     'base' y 'upgraded' actúan como filtro+orden: muestran solo los
 *     vouchers de ese tier, ordenados alfabéticamente. Conviene
 *     ponerlos en el select de "Orden" porque conceptualmente
 *     reordenan/filtran la lista igual que los otros sorts.
 *   El resto: vacío → FilterBar usa las opciones por defecto.
 */
const sortOptions = computed(() => {
  if (currentSub.value === "vouchers") {
    return [
      { value: "name", label: "Orden: A-Z" },
      { value: "base", label: "Orden: BASE" },
      { value: "upgraded", label: "Orden: UPGRADED" },
    ];
  }
  return [];
});

const typeOptions = computed(() => {
  if (currentSub.value === "booster-packs") {
    return [
      { value: "all", label: "Tipo: Todos" },
      { value: "ARCANA", label: "Tipo: Arcana" },
      { value: "CELESTIAL", label: "Tipo: Celestial" },
      { value: "STANDARD", label: "Tipo: Standard" },
      { value: "BUFFOON", label: "Tipo: Buffoon" },
      { value: "SPECTRAL", label: "Tipo: Spectral" },
    ];
  }
  if (currentSub.value === "card-modifiers") {
    return [
      { value: "all", label: "Tipo: Todos" },
      { value: "enhancements", label: "Tipo: Enhancements" },
      { value: "editions", label: "Tipo: Editions" },
      { value: "seals", label: "Tipo: Seals" },
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

const filteredDecks = computed(() => {
  let list = applyBaseFilters(decks.value);
  list = list.filter(statusMatches);
  return sortItems(list);
});

/**
 * VALES tienen su propia lógica de filtrado/orden:
 *   · search + status (heredados)
 *   · sort: 'name' = A-Z, 'base' = solo voucher_tier=BASE, 'upgraded'
 *           = solo voucher_tier=UPGRADED. En los dos últimos también
 *           ordenamos alfabético.
 *
 * Antes faltaba `statusMatches` (bug reportado: el filtro estado se
 * mostraba pero no afectaba a la lista).
 */
const filteredVouchers = computed(() => {
  let list = applyBaseFilters(vouchers.value);
  list = list.filter(statusMatches);
  if (filters.value.sort === "base") {
    list = list.filter((v) => String(v.voucher_tier).toUpperCase() === "BASE");
  } else if (filters.value.sort === "upgraded") {
    list = list.filter((v) => String(v.voucher_tier).toUpperCase() === "UPGRADED");
  }
  // Cualquier opción (incluido 'name') ordena alfabéticamente.
  return [...list].sort((a, b) => (a.name || "").localeCompare(b.name || ""));
});

/**
 * Booster packs: tras filtros base y status, agrupar por pack_type
 * respetando el orden visual de PACK_TYPES. Si hay filtro `type`,
 * solo se devuelve el grupo correspondiente.
 */
const groupedBoosterPacks = computed(() => {
  let list = applyBaseFilters(boosterPacks.value);
  list = list.filter(statusMatches);
  if (filters.value.type && filters.value.type !== "all") {
    list = list.filter((p) => String(p.pack_type).toUpperCase() === filters.value.type);
  }
  return PACK_TYPES.map((t) => {
    const items = list
      .filter((p) => String(p.pack_type).toUpperCase() === t.id)
      .sort((a, b) => {
        const oa = PACK_SIZE_ORDER[a.size] ?? 99;
        const ob = PACK_SIZE_ORDER[b.size] ?? 99;
        if (oa !== ob) return oa - ob;
        return (a.item_number ?? a.id) - (b.item_number ?? b.id);
      });
    return { packType: t.id, label: t.label, color: t.color, items };
  }).filter((g) => g.items.length);
});

function enrichedPackName(pack) {
  const sized = pack.size ? `${pack.name} ${pack.size}` : pack.name;
  return { ...pack, name: sized };
}

/**
 * Agrupa los grupos de pack-types de 2 en 2 para renderizarlos en
 * filas de 2 columnas. El último grupo, si el número es impar, queda
 * solo en su fila (la CSS de .packs-row--solo lo centra con la misma
 * anchura que una columna en una fila normal — así SPECTRAL se ve
 * IGUAL de grande que ARCANA, CELESTIAL, etc., no más pequeño).
 */
const packRows = computed(() => {
  const groups = groupedBoosterPacks.value;
  const rows = [];
  for (let i = 0; i < groups.length; i += 2) {
    rows.push(groups.slice(i, i + 2));
  }
  return rows;
});

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

// ── Counters ─────────────────────────────────────────────────────
const subtabCount = computed(() => {
  if (currentSub.value === "decks") return filteredDecks.value.length;
  if (currentSub.value === "vouchers") return filteredVouchers.value.length;
  if (currentSub.value === "booster-packs")
    return groupedBoosterPacks.value.reduce((acc, g) => acc + g.items.length, 0);
  if (currentSub.value === "card-modifiers")
    return filteredModifierGroups.value.reduce((acc, g) => acc + g.items.length, 0);
  return 0;
});

/**
 * Total y desbloqueados a través de los 4 sub-tabs — para la
 * ProgressBar global. Se calcula sobre las listas COMPLETAS (sin
 * filtros) para que el porcentaje refleje el estado real, no el
 * filtrado.
 */
const allItems = computed(() => [
  ...decks.value,
  ...vouchers.value,
  ...boosterPacks.value,
  ...(modifiers.value.enhancements || []),
  ...(modifiers.value.editions || []),
  ...(modifiers.value.seals || []),
]);
const globalTotal = computed(() => allItems.value.length);
const globalUnlocked = computed(() => allItems.value.filter((it) => !isLocked(it)).length);

// ── Selección + tooltip ──────────────────────────────────────────
const selectedItem = ref(null);
const tooltip = ref(null);
let hoverTimer = null;

function onSelect(item, kind, modKey = null) {
  // Comprobación estricta para evitar toggle
  if (
    selectedItem.value &&
    selectedItem.value.id === item.id &&
    selectedItem.value._kind === kind
  ) {
    return; // Ya está seleccionado, no hagas nada
  }

  const enriched = { ...item, _kind: kind, _modKey: modKey };

  // Lógica para traer el preview de vouchers si aplica
  if (kind === "voucher" && item.next_voucher_id) {
    const upgrade = vouchers.value.find((v) => v.id === item.next_voucher_id);
    if (upgrade) {
      enriched._nextVoucher = { id: upgrade.id, name: upgrade.name, image_url: upgrade.image_url };
    }
  }
  selectedItem.value = enriched;
}

/**
 * Desbloqueo manual desde el detail panel.
 *
 * POST /api/me/unlocks { unlockable_id, unlocked: true } — endpoint
 * compartido para jokers/decks/vouchers/booster-packs (todos son
 * Unlockable). Card-modifiers no aplica (no son Unlockable), pero
 * nunca aparecen como locked, así que el botón ni se renderiza para
 * ellos.
 *
 * Tras el POST mutamos el item localmente (y selectedItem) añadiendo
 * `unlocked_for_me: true`. Eso hace que isItemLocked devuelva false al
 * instante y la carta se ve desbloqueada sin esperar a un re-fetch.
 * Para decks el cambio persiste tras recargar (porque /api/me/decks
 * devuelve el overlay); para vouchers/packs persiste en BD pero no
 * se ve hasta que el backend exponga /api/me/vouchers y
 * /api/me/booster-packs.
 */
async function onManualUnlock(item) {
  if (!item) return;
  try {
    await unlockItem(item.id);
    mutateLocally(item, { unlocked_for_me: true, unlocked_at: new Date().toISOString() });
  } catch (e) {
    console.error("[CollectionView] manual unlock failed", e);
    // 401 = sesión caducada. Abrimos el AuthModal — es la acción que
    // el usuario necesita; un alert técnico no le ayuda a recuperarse.
    if (e?.response?.status === 401) {
      authStore.openAuthModal();
      return;
    }
    alert("No se pudo marcar como desbloqueado. " + (e.message || ""));
  }
}

function onStakeUpdated(data) {
  // data viene de { id, highest_stake_order }

  // 1. Identificamos el array correcto según la pestaña actual
  let targetArray;
  if (currentSub.value === "decks") {
    targetArray = decks.value;
  } else {
    // Si no es un mazo, no tenemos nada que actualizar en esta vista
    return;
  }

  // 2. Buscamos el item en la lista y lo actualizamos
  const item = targetArray.find((i) => i.id === data.id);
  if (item) {
    item.highest_stake_order = data.highest_stake_order;
  }

  // 3. Si el item está seleccionado en el panel derecho, actualizamos también el panel
  if (selectedItem.value && selectedItem.value.id === data.id) {
    selectedItem.value.highest_stake_order = data.highest_stake_order;
  }
}

function mutateLocally(item, patch) {
  const kind = selectedItem.value?._kind;
  let arr = null;
  if (kind === "deck") arr = decks.value;
  else if (kind === "voucher") arr = vouchers.value;
  else if (kind === "pack") arr = boosterPacks.value;
  if (arr) {
    const target = arr.find((x) => x.id === item.id);
    if (target) Object.assign(target, patch);
  }
  if (selectedItem.value) {
    selectedItem.value = { ...selectedItem.value, ...patch };
  }
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

/* Toolbar: subtabs + FilterBar en la misma fila ──────────────── */
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  align-items: stretch;

  /* FilterBar es un componente hijo, scope-cross con :deep. */
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

  &:hover {
    transform: scale(1.05);
    filter: brightness(1.15);
  }
  &:active {
    transform: scale(0.95);
  }
}
.subtab--decks {
  background: #e84040;
}
.subtab--booster-packs {
  background: #f59e0b;
}
.subtab--vouchers {
  background: #3b82f6;
}
.subtab--card-modifiers {
  background: #22c55e;
}
.subtab--active {
  filter: brightness(1.25);
}

/* Layout ────────────────────────────────────────────────────── */
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

/* Booster packs ────────────────────────────────────────────────
 * Render en filas explícitas (computed packRows) en lugar de un grid
 * 2D con grid-column: 1/-1. Más fácil de controlar y SPECTRAL queda
 * EXACTAMENTE del mismo tamaño que las otras secciones cuando se
 * queda solo en su fila (no es "más pequeño" como decía el feedback).
 */
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

/*
 * Fila con UN solo grupo (típicamente SPECTRAL al final).
 * Usamos flex con justify-content: center y forzamos al hijo a la
 * misma anchura que tendría como columna en una fila 1fr 1fr:
 * `(100% - 28) / 2` = `calc(50% - 14px)`.
 * El tamaño final del section solo y de las internas (cartas) queda
 * idéntico a los grupos de filas pareadas.
 */
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

/* Detail column ────────────────────────────────────────────── */
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

/* ── Animaciones de Entrada ───────────────────────────────────────── */
/*
 * Animación estilo "repartir carta" (Deal) para la vista de colección.
 * Cae verticalmente con escala elástica protegiendo los transforms del arco.
 */
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
</style>
