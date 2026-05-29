/**
 * Servicio de Logros (Achievements).
 *
 * A diferencia de jokers/decks/vouchers, los logros NO son una subclase
 * de `Unlockable` — viven en su propia tabla `achievements` con un
 * pivot `user_achievements`. Por eso no comparten el endpoint
 * `/api/me/unlocks` y necesitan su propio par de rutas.
 *
 * Endpoints consumidos:
 *   - GET  /api/achievements          → catálogo público (sin overlay).
 *   - GET  /api/me/achievements       → catálogo + overlay del usuario
 *                                       autenticado (`unlocked_for_me`,
 *                                       `unlocked_at`).
 *   - POST /api/me/achievements/unlock { achievement_id, unlocked }
 *                                     → marca/desmarca manualmente para
 *                                       cuentas SIN steam_id.
 *
 * Forma esperada de cada logro:
 *   {
 *     id, name, description, icon_url,
 *     // overlay solo en /api/me/achievements:
 *     unlocked_for_me?: boolean,
 *     unlocked_at?: string,
 *   }
 *
 * Si el backend todavía no expone POST /api/me/achievements/unlock, el
 * botón "marcar como desbloqueado" alertará con un mensaje útil — el
 * código frontend ya está listo para activarse cuando se cree la ruta.
 *
 * Notas para implementar el endpoint POST (Flask, en `app/api/me.py`):
 *
 *   @me_progress_bp.route("/achievements/unlock", methods=["POST"])
 *   @require_auth
 *   def set_my_achievement():
 *       payload = request.get_json() or {}
 *       achievement_id = payload.get("achievement_id")
 *       unlocked = bool(payload.get("unlocked", True))
 *       row = UserAchievement.query.filter_by(
 *           user_id=g.user.id, achievement_id=achievement_id,
 *       ).first()
 *       if not row:
 *           row = UserAchievement(
 *               user_id=g.user.id, achievement_id=achievement_id,
 *           )
 *           db.session.add(row)
 *       row.unlocked = unlocked
 *       row.unlocked_at = func.now() if unlocked else None
 *       db.session.commit()
 *       return jsonify({"ok": True})
 *
 * Para usuarios con `steam_id` el desbloqueo se hace automático desde
 * el sync de Steam (rama backend pendiente: leer GetPlayerAchievements
 * y crear UserAchievement por cada `achieved=1`). El frontend lo único
 * que hace es ocultar el botón manual cuando detecta `user.steam_id`.
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
 * Helper paginador. Pide la primera página y, si hay más, las restantes
 * en paralelo. Devuelve la lista concatenada de `items`.
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
        const r = await api.get(path, {
          params: { ...params, page },
        });

        items = items.concat(r.data.items);
      }
    }
    return items;
  } catch (e) {
    throw wrapError(e, ctx);
  }
}

/**
 * Carga todos los logros. Con `authenticated=true` usa `/api/me/achievements`
 * (incluye overlay `unlocked_for_me`); sin auth, `/api/achievements`.
 *
 * @param {object} [opts]
 * @param {boolean} [opts.authenticated]
 * @returns {Promise<Array<object>>}
 */
export async function fetchAllAchievements({ authenticated = false } = {}) {
  const path = authenticated ? "/api/me/achievements" : "/api/achievements";
  return fetchAllPages(path);
}

/**
 * Marca un logro como desbloqueado para el usuario actual. SOLO se debe
 * llamar para cuentas SIN `steam_id` — los usuarios con cuenta Steam
 * desbloquean automáticamente al sincronizar.
 *
 * @param {number} achievementId
 * @returns {Promise<void>}
 */
export async function unlockAchievement(achievementId, unlocked = true) {
  await api.post("/api/me/achievements/unlock", {
    achievement_id: achievementId,
    unlocked,
  });
}
