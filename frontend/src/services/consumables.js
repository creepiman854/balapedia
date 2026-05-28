/**
 * Servicio de consumibles (tarots, planets, spectrals).
 *
 * Endpoint consumido:
 *   - GET /api/consumables?type=TAROT|PLANET|SPECTRAL  — catálogo público.
 *
 * Pendiente backend:
 *   - GET /api/me/consumables — equivalente autenticado con overlay
 *     `unlocked_for_me`. NO existe todavía: `me.py` solo expone jokers,
 *     decks y achievements en /api/me. Cuando se añada, aquí se cambia
 *     el path por el autenticado.
 *
 * Forma del item (de `ConsumableSchema`):
 *   id, type ('TAROT'|'PLANET'|'SPECTRAL'), item_number,
 *   name, description, image_url, unlock_condition, unlock_factor,
 *   buy_price, sell_price, in_shop.
 *
 * Errores: si el backend responde 4xx/5xx, propagamos un Error con
 * el status + mensaje del backend para que la vista pueda mostrarlo
 * (en vez de un genérico "no se pudo cargar"). Esto ahorra horas de
 * debug cuando un endpoint cambia de nombre o de filtros.
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
    return new Error(`${contextPath} → sin respuesta del backend (¿flask corriendo en :8080?)`);
  }
  return e;
}

/**
 * Recolecta TODAS las páginas de consumibles del tipo indicado.
 * @param {string} type  TAROT | PLANET | SPECTRAL
 * @returns {Promise<Array<object>>}
 */
export async function fetchConsumablesByType(type) {
  const path = "/api/consumables";
  const params = { type, per_page: 100, page: 1 };

  try {
    const first = await api.get(path, { params });
    let items = [...first.data.items];
    const totalPages = first.data.total_pages || 1;

    if (totalPages > 1) {
      for (let page = 2; page <= totalPages; page++) {
        const r = await api.get(path, {
          params: { ...params, page },
        });

        items = items.concat(r.data.items);
      }
    }
    return items;
  } catch (e) {
    throw wrapError(e, `${path}?type=${type}`);
  }
}

/**
 * Detalle de un consumible por id.
 * @param {number} id
 * @returns {Promise<object>}
 */
export async function fetchConsumableById(id) {
  try {
    const { data } = await api.get(`/api/consumables/${id}`);
    return data;
  } catch (e) {
    throw wrapError(e, `/api/consumables/${id}`);
  }
}
