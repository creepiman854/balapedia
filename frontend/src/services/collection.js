/**
 * Servicio de Colección.
 *
 * Endpoints consumidos:
 *   - GET  /api/decks               /  /api/me/decks
 *   - GET  /api/vouchers            /  /api/me/vouchers
 *   - GET  /api/booster-packs       /  /api/me/booster-packs
 *   - GET  /api/challenge-decks     /  /api/me/challenge-decks
 *   - GET  /api/card-modifiers      (sin /me/* — modifiers no son Unlockable)
 *   - POST /api/me/unlocks          (compartido para todos los Unlockables;
 *                                    incluye re-lock con unlocked=false)
 *
 * Forma de los items (heredan de Unlockable):
 *   id, type, item_number, name, description, image_url,
 *   unlock_condition, wiki_url, unlock_factor, locked_image_url?
 *   + campos propios de cada subclase:
 *     - Deck:          (sin extras, todo viene del padre)
 *     - Voucher:       voucher_tier ('BASE' | 'UPGRADED'), buy_price
 *     - BoosterPack:   pack_type ('ARCANA'|...), size ('NORMAL'|...), cost
 *     - ChallengeDeck: modifier, starter, banned, deck_description
 *     - CardModifier (no es subclase de Unlockable, tabla flat):
 *         modifier_type ('ENHANCEMENT' | 'EDITION' | 'SEAL'), name, effect
 *
 * `locked_image_url` (Fase 2) lo expone el backend solo para Jokers,
 * Vouchers y Decks — los demás subtipos lo reciben como `undefined`.
 *
 * Errores: envolvemos los AxiosError en Error con status + mensaje del
 * backend para diagnosticar a la primera (igual que services/consumables.js).
 */
import { api } from "./api";
import { useDictionaryStore } from "@/stores/dictionary";

function wrapError(e, contextPath) {
  if (e.response) {
    const status = e.response.status;
    const data = e.response.data || {};
    const detail =
      (data.details && JSON.stringify(data.details)) ||
      data.message ||
      data.error ||
      e.response.statusText ||
      `HTTP ${status}`;
    const err = new Error(`${contextPath} → ${status}: ${detail}`);
    err.cause = e;
    return err;
  }
  if (e.request) {
    return new Error(`${contextPath} → no response from backend (is Flask running on :8080?)`);
  }
  return e;
}

/**
 * Reintenta UNA vez con back-off si la primera llamada falla con 500.
 * Pensado para el cold-start del backend: a veces la primera request
 * después de levantar Flask falla por timing (auth + DB warm-up) y
 * un segundo intento ~700 ms después funciona sin problema.
 * Errores que no son 500 (4xx, network) NO se reintentan — son
 * deterministas y un retry no los va a arreglar.
 */
async function withColdStartRetry(fn) {
  try {
    return await fn();
  } catch (e) {
    const is500 = e?.response?.status === 500;
    if (!is500) throw e;
    await new Promise((r) => setTimeout(r, 700));
    return await fn();
  }
}

/**
 * Helper paginador. Pide las páginas en SECUENCIA. NO usar Promise.all:
 * el plan de hosting actual del backend tiene `max_user_connections=5`
 * y abrir 4+ conexiones a la vez desde una sola vista satura el pool.
 */
async function fetchAllPages(path, extraParams = {}, contextLabel = null) {
  const ctx = contextLabel ?? path;
  const params = { per_page: 100, page: 1, ...extraParams };
  try {
    const first = await withColdStartRetry(() => api.get(path, { params }));
    let items = [...first.data.items];
    const totalPages = first.data.total_pages || 1;
    if (totalPages > 1) {
      for (let page = 2; page <= totalPages; page++) {
        const r = await api.get(path, { params: { ...params, page } });
        items = items.concat(r.data.items);
      }
    }
    const dictStore = useDictionaryStore();
    dictStore.registerItems(items);

    return items;
  } catch (e) {
    throw wrapError(e, ctx);
  }
}

// ── Decks ─────────────────────────────────────────────────────────
/**
 * Si `authenticated` es true se pide /api/me/decks (con overlay
 * `unlocked_for_me`); si no, /api/decks (público, sin overlay).
 */
export async function fetchAllDecks({ authenticated = false } = {}) {
  const path = authenticated ? "/api/me/decks" : "/api/decks";
  return fetchAllPages(path);
}

// ── Vouchers ──────────────────────────────────────────────────────
/**
 * Si `authenticated` es true se pide /api/me/vouchers (con overlay
 * `unlocked_for_me` + `unlocked_at` + `highest_stake_order`); si no,
 * /api/vouchers (público, sin overlay).
 *
 * Importante para el cascade de Steam sync: BAL_07 (Card Player) y
 * BAL_08 (Card Discarder) comparten unlock_factor con Nacho Tong y
 * Recyclomancy respectivamente. Sin el endpoint autenticado el cascade
 * crea las filas UserUnlock pero el frontend no las puede ver.
 */
export async function fetchAllVouchers({ authenticated = false } = {}) {
  const path = authenticated ? "/api/me/vouchers" : "/api/vouchers";
  return fetchAllPages(path);
}

// ── Booster Packs ─────────────────────────────────────────────────
/**
 * Si `authenticated` es true se pide /api/me/booster-packs (overlay
 * `unlocked_for_me`); si no, /api/booster-packs.
 *
 * En vanilla Balatro los sobres son "available from start" sin
 * unlock_factor, así que el overlay siempre devuelve unlocked_for_me=false.
 * Exponer el endpoint mantiene la simetría de la API y deja la puerta
 * abierta a mods comunitarios con sobres con condiciones de desbloqueo.
 */
export async function fetchAllBoosterPacks({ authenticated = false } = {}) {
  const path = authenticated ? "/api/me/booster-packs" : "/api/booster-packs";
  return fetchAllPages(path);
}

// ── Challenge Decks ───────────────────────────────────────────────
/**
 * Si `authenticated` es true se pide /api/me/challenge-decks (overlay
 * `unlocked_for_me`); si no, /api/challenge-decks (público).
 *
 * Crítico para el cascade de Rule Breaker (BAL_23) sea visible:
 * cuando el achievement se desbloquea, el resolver del backend crea las
 * filas UserUnlock para los 20 challenge decks, pero SIN este endpoint
 * autenticado el frontend leería del público y los vería siempre locked.
 */
export async function fetchAllChallengeDecks({ authenticated = false } = {}) {
  const path = authenticated ? "/api/me/challenge-decks" : "/api/challenge-decks";
  return fetchAllPages(path);
}

// ── Card Modifiers ────────────────────────────────────────────────
/**
 * @param {string} modifierType  ENHANCEMENT | EDITION | SEAL
 */
export async function fetchCardModifiers(modifierType) {
  return fetchAllPages(
    "/api/card-modifiers",
    { modifier_type: modifierType },
    `/api/card-modifiers?modifier_type=${modifierType}`,
  );
}

/**
 * Trae TODOS los card modifiers en una sola request (sin filtro de tipo)
 * y los agrupa por `modifier_type` en el cliente.
 *
 * @returns {Promise<{enhancements: Array, editions: Array, seals: Array}>}
 */
export async function fetchAllCardModifiers() {
  const all = await fetchAllPages("/api/card-modifiers");
  const grouped = { enhancements: [], editions: [], seals: [] };
  for (const item of all) {
    const type = String(item.modifier_type || "").toUpperCase();
    if (type === "ENHANCEMENT") grouped.enhancements.push(item);
    else if (type === "EDITION") grouped.editions.push(item);
    else if (type === "SEAL") grouped.seals.push(item);
  }
  return grouped;
}

// ── Manual unlock / re-lock ───────────────────────────────────────
/**
 * Marca un Unlockable como desbloqueado para el usuario actual.
 *
 * Endpoint compartido para jokers/decks/vouchers/booster-packs/
 * consumables/challenge-decks — todos comparten el id namespace de la
 * tabla padre `unlockables`, así que `POST /api/me/unlocks` con
 * `{ unlockable_id, unlocked }` cubre los seis subtipos.
 *
 * @param {number} unlockableId
 */
export async function unlockItem(unlockableId) {
  await api.post("/api/me/unlocks", { unlockable_id: unlockableId, unlocked: true });
}

/**
 * Re-bloquea un Unlockable que el usuario había desbloqueado
 * manualmente (o por cascade de Steam). El backend lo persiste con
 * `unlocked=false`; tras esto, `/api/me/<subtipo>` lo devolverá con
 * `unlocked_for_me: false`.
 *
 * @param {number} unlockableId
 */
export async function relockItem(unlockableId) {
  await api.post("/api/me/unlocks", { unlockable_id: unlockableId, unlocked: false });
}
