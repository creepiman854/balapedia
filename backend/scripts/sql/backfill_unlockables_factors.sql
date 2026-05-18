-- =============================================================================
-- Backfill de unlockables.unlock_factor_id para items con shared unlock
-- =============================================================================
-- Enlaza los items (jokers, decks, vouchers) que comparten condición de
-- desbloqueo con uno de los 31 achievements. Cuando el usuario cumpla la
-- condición y se le dispare el achievement, el servicio de auto-unlock
-- propagará el unlock a estos items vía el shared unlock_factor_id.
--
-- El matching se hace por (type, name) — más estable que por unlock_condition
-- (que tiene inconsistencias en redacción).
--
-- Idempotente: la UPDATE deja la fila en el mismo estado si ya estaba
-- enlazada al factor correcto.
-- =============================================================================

-- ---- JOKERS (10 confirmados) ------------------------------------------------
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'REACH_ANTE_4')           WHERE type = 'JOKER' AND name = 'Showman';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'REACH_ANTE_8')           WHERE type = 'JOKER' AND name = 'Flower Pot';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_RUN')                WHERE type = 'JOKER' AND name = 'Blueprint';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'HAVE_400_MONEY')         WHERE type = 'JOKER' AND name = 'Satellite';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_12_OR_FEWER_ROUNDS') WHERE type = 'JOKER' AND name = 'Merry Andy';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'SCORE_10K_SINGLE_HAND')  WHERE type = 'JOKER' AND name = 'Oops! All 6s';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'SCORE_1M_SINGLE_HAND')   WHERE type = 'JOKER' AND name = 'The Idol';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'SCORE_100M_SINGLE_HAND') WHERE type = 'JOKER' AND name = 'Stuntman';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_ALL_PLANETS')   WHERE type = 'JOKER' AND name = 'Astronomer';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_ALL_TAROTS')    WHERE type = 'JOKER' AND name = 'Cartomancer';

-- ---- VOUCHERS (2 confirmados) -----------------------------------------------
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'PLAY_2500_CARDS')    WHERE type = 'VOUCHER' AND name = 'Nacho Tong';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCARD_2500_CARDS') WHERE type = 'VOUCHER' AND name = 'Recyclomancy';

-- ---- DECKS (2 pendientes de confirmar nombre) -------------------------------
-- Descomentar y ajustar el `name` exacto cuando se confirme cómo están
-- guardados Zodiac y Anaglyph en la tabla unlockables.
--
-- UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_RED_STAKE')   WHERE type = 'DECK' AND name = '<<Zodiac o Zodiac Deck>>';
-- UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_BLACK_STAKE') WHERE type = 'DECK' AND name = '<<Anaglyph o Anaglyph Deck>>';

-- Verificación: deben aparecer 12 (o 14 si añadimos los decks) filas con factor
SELECT
  u.type,
  u.name,
  uf.code AS factor_code,
  uf.description AS factor_description
FROM unlockables u
JOIN unlock_factors uf ON uf.id = u.unlock_factor_id
ORDER BY u.type, u.name;

-- Conteo global de items con factor enlazado (debería crecer monotónicamente
-- conforme cubramos más casos)
SELECT
  type,
  COUNT(*)                          AS total,
  COUNT(unlock_factor_id)           AS with_factor,
  COUNT(*) - COUNT(unlock_factor_id) AS without_factor
FROM unlockables
GROUP BY type
ORDER BY type;
