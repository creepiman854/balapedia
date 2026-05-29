/**
 * Servicio de datos de referencia del juego (Blinds, Tags).
 *
 * Endpoints consumidos (todos públicos, sin auth):
 *   - GET /api/blinds
 *   - GET /api/tags
 *
 * Estas dos entidades NO son `Unlockable`: viven en tablas flat propias
 * (`blinds`, `tags`) y son referencia informativa. El usuario nunca las
 * "desbloquea" — pero las cuento en la barra de progreso global de la
 * Colección como siempre-completadas para reflejar que su presencia en
 * la app es 100% (decisión de UX, no de dato).
 *
 * Forma de cada item:
 *   Blind: { id, name, blind_type ('SMALL'|'BIG'|'BOSS'), description,
 *            image_url, ante ('Any' | número como string), score_multiplier,
 *            reward_money, matador_compatible, wiki_url }
 *   Tag:   { id, name, description, image_url, ante, unlock_condition,
 *            wiki_url }
 *
 * Errores: mismo patrón `wrapError` que el resto de servicios para
 * propagar status + mensaje del backend al usuario.
 *
 * Mismo paginador secuencial que `collection.js` para respetar el límite
 * de 5 conexiones simultáneas del pool MySQL. No usamos Promise.all.
 */
import { api } from "./api";

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
    return new Error(`${contextPath} → no response from backend (is Flask running?)`);
  }
  return e;
}

/**
 * Reintenta UNA vez con 700 ms de back-off si la primera llamada falla
 * con 500. Mismo patrón que `services/collection.js` — evita el típico
 * 500 inicial por timing del pool MySQL (max_user_connections=5).
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
 * Helper paginador secuencial. Mismo patrón que el resto de servicios
 * para no abrir múltiples conexiones a la vez.
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
    return items;
  } catch (e) {
    throw wrapError(e, ctx);
  }
}

/**
 * Lista completa de Blinds del juego.
 *
 * En vanilla Balatro son 2 (Small + Big) + ~30 Boss Blinds individuales,
 * todos en la misma tabla discriminada por `blind_type`. Los Boss Blinds
 * de tipo "Finisher" se identifican por `ante === "8"` (los demás tienen
 * `ante === "Any"`).
 *
 * Sin paginación real esperada (~32 items totales) — el `per_page=100`
 * cubre el caso "vanilla", el paginador secuencial cubre futuros mods
 * con más Blinds.
 *
 * @returns {Promise<Array<object>>}
 */
export async function fetchAllBlinds() {
  return fetchAllPages("/api/blinds");
}

/**
 * Lista completa de Tags del juego.
 *
 * 24 tags en vanilla. Algunos requieren descubrir un Joker o edición
 * primero (`unlock_condition`), pero el descubrimiento se gestiona dentro
 * de la partida — la app los expone todos en el catálogo informativo,
 * no como Unlockables.
 *
 * @returns {Promise<Array<object>>}
 */
export async function fetchAllTags() {
  return fetchAllPages("/api/tags");
}
