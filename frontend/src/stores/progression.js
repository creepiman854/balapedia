/**
 * Store Pinia de progresión: stakes y stickers del catálogo.
 *
 * Datos que casi nunca cambian (las 8 stakes y los stickers del juego)
 * se cachean aquí para que todos los componentes que necesiten las
 * imágenes/nombres (ItemCard overlay, StakeSelector, ItemDetailPanel)
 * compartan la misma fuente sin re-fetchear cada uno por separado.
 *
 * Se inicializa lazy: la primera vez que un componente llama a `init()`,
 * se disparan los dos fetches. Las siguientes veces son no-op.
 */
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { fetchAllStakes, fetchAllStickers } from "@/services/progression";

export const useProgressionStore = defineStore("progression", () => {
  const stakes = ref([]);
  const stickers = ref([]);
  const loaded = ref(false);
  const loading = ref(false);

  /**
   * Stickers filtrados a los de tipo STAKE (los que representan
   * progresión White→Gold). Excluye los IN_RUN (Eternal, Perishable,
   * Rental) que no participan en la progresión por dificultad.
   *
   * Cada uno tiene un `stake` nested con `stake_order` que es la key
   * de match con `UserStickerApplication.highest_stake_order`.
   *
   * Se usa para mostrar los stickers de JOKERS.
   */
  const progressionStickers = computed(() =>
    stickers.value
      .filter((s) => s.stake !== null && s.stake !== undefined)
      .sort((a, b) => (a.stake?.stake_order ?? 0) - (b.stake?.stake_order ?? 0)),
  );

  /**
   * Stakes ordenados por stake_order (1=White → 8=Gold).
   * Se usa para mostrar los stakes de DECKS.
   */
  const sortedStakes = computed(() =>
    [...stakes.value].sort((a, b) => a.stake_order - b.stake_order),
  );

  /**
   * Mapa rápido: stake_order → imagen del sticker (para jokers).
   * Ej: stickersMap[8] = { image_url: "...", name: "Gold Sticker", ... }
   */
  const stickersByOrder = computed(() => {
    const map = {};
    for (const s of progressionStickers.value) {
      if (s.stake?.stake_order != null) {
        map[s.stake.stake_order] = s;
      }
    }
    return map;
  });

  /**
   * Mapa rápido: stake_order → imagen del stake (para decks).
   * Ej: stakesMap[8] = { image_url: "...", name: "Gold Stake", ... }
   */
  const stakesByOrder = computed(() => {
    const map = {};
    for (const s of sortedStakes.value) {
      map[s.stake_order] = s;
    }
    return map;
  });

  /**
   * Devuelve la imagen + nombre del sticker/stake para un item dado.
   *
   * @param {number} stakeOrder  1-8 (highest_stake_order del overlay)
   * @param {string} itemType    'JOKER' | 'DECK' (determina si buscar
   *                             en stickers o en stakes)
   * @returns {{ image_url, name, description } | null}
   */
  function getProgressionInfo(stakeOrder, itemType) {
    if (!stakeOrder || stakeOrder < 1) return null;
    if (itemType === "JOKER") {
      const sticker = stickersByOrder.value[stakeOrder];
      if (!sticker) return null;
      return {
        image_url: sticker.image_url,
        name: sticker.name,
        description: sticker.description || "",
      };
    }
    // DECK
    const stake = stakesByOrder.value[stakeOrder];
    if (!stake) return null;
    return {
      image_url: stake.image_url,
      name: stake.name,
      description: stake.effect_description || "",
    };
  }

  /**
   * Carga el catálogo si no está ya cargado. Idempotente.
   * Las vistas (JokersView, CollectionView) llaman a esto en onMounted.
   */
  async function init() {
    if (loaded.value || loading.value) return;
    loading.value = true;
    try {
      const s = await fetchAllStakes();
      const st = await fetchAllStickers();
      
      stakes.value = s;
      stickers.value = st;
      loaded.value = true;
    } catch (e) {
      console.error("[progression store] failed to load catalog:", e);
    } finally {
      loading.value = false;
    }
  }

  return {
    stakes,
    stickers,
    loaded,
    loading,
    progressionStickers,
    sortedStakes,
    stickersByOrder,
    stakesByOrder,
    getProgressionInfo,
    init,
  };
});
