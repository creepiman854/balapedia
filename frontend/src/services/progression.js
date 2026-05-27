/**
 * Servicio de progresión (stakes, stickers, sticker applications).
 *
 * Cubre dos consultas de catálogo (datos públicos que rara vez cambian)
 * y una mutación autenticada:
 *
 *   - GET /api/stakes          → las 8 dificultades del juego con su
 *                                 imagen, color, effect_description.
 *   - GET /api/stickers        → todos los stickers; el caller filtra
 *                                 sticker_type=STAKE para progresión.
 *   - POST /api/me/sticker-applications
 *                              → aplica manualmente un sticker a un
 *                                 joker/deck del usuario (solo promociona,
 *                                 nunca baja).
 *
 * Los GET son catálogo: se piden una sola vez y se cachean en refs del
 * componente que los consume (o en un Pinia store si se quiere
 * compartir). No tienen auth: cualquiera puede verlos.
 *
 * El POST es autenticado: permite progreso manual tanto para usuarios
 * normales como para cuentas con Steam vinculada. Las aplicaciones con
 * source=MANUAL coexisten con las generadas por sincronización Steam.
 */
import { api } from "./api";

// ── Catálogo ─────────────────────────────────────────────────────────

/**
 * Los 8 stakes del juego (White → Gold), con image_url, color,
 * effect_description. Ordenados por stake_order.
 *
 * Shape de cada item:
 *   { id, name, stake_order, color, effect_description, image_url,
 *     unlocks_deck_name, wiki_url }
 *
 * @returns {Promise<Array>}
 */
export async function fetchAllStakes() {
  const { data } = await api.get("/api/stakes", { params: { per_page: 100 } });
  return data.items || [];
}

/**
 * Todos los stickers del juego. Incluye tanto IN_RUN (Eternal,
 * Perishable, Rental) como STAKE (White → Gold). El caller filtra
 * por `sticker_type` según lo que necesite.
 *
 * Shape de cada item:
 *   { id, name, sticker_type, description, image_url, sticker_order,
 *     wiki_url, stake: { id, name, stake_order, color } | null }
 *
 * Para progresión, filtrar: `stickers.filter(s => s.stake !== null)`.
 * El `stake.stake_order` es la key de match con
 * `UserStickerApplication.highest_stake_order`.
 *
 * @returns {Promise<Array>}
 */
export async function fetchAllStickers() {
  const { data } = await api.get("/api/stickers", { params: { per_page: 100 } });
  return data.items || [];
}

// ── Mutación ─────────────────────────────────────────────────────────

/**
 * Aplica o promociona un sticker (stake progression) a un Joker o Deck.
 *
 * Solo promociona: si el usuario ya tiene highest_stake_order >= al
 * solicitado, es no-op. La response incluye el highest_stake_order
 * final (que puede ser mayor que el solicitado si ya estaba por encima).
 *
 * @param {number} unlockableId  id del Joker o Deck (tabla unlockables)
 * @param {number} stakeOrder    1=White, 2=Red, ..., 8=Gold
 * @returns {Promise<{ ok: boolean, highest_stake_order: number }>}
 */
export async function setStickerApplication(unlockableId, stakeOrder) {
  const { data } = await api.post("/api/me/sticker-applications", {
    unlockable_id: unlockableId,
    stake_order: stakeOrder,
  });
  return data;
}
