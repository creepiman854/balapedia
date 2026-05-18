-- =============================================================================
-- Backfill DECKS — completa los 2 decks con shared unlock que faltaban
-- =============================================================================
-- Zodiac Deck y Anaglyph Deck no aparecieron en el SELECT inicial porque en la
-- tabla unlockables están guardados con el sufijo " Deck" (convención
-- aplicada a todos los decks: "Red Deck", "Plasma Deck", etc.).
--
-- Idempotente: la UPDATE deja la fila en el mismo estado si ya estaba enlazada.
-- =============================================================================

UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_RED_STAKE')   WHERE type = 'DECK' AND name = 'Zodiac Deck';
UPDATE unlockables SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_BLACK_STAKE') WHERE type = 'DECK' AND name = 'Anaglyph Deck';

-- Verificación: ahora deben aparecer 14 items con factor (10 jokers + 2 vouchers + 2 decks)
SELECT
  u.type,
  u.name,
  uf.code        AS factor_code,
  uf.description AS factor_description
FROM unlockables u
JOIN unlock_factors uf ON uf.id = u.unlock_factor_id
ORDER BY u.type, u.name;

-- Conteo por tipo: DECK ahora debe mostrar with_factor = 2
SELECT
  type,
  COUNT(*)                           AS total,
  COUNT(unlock_factor_id)            AS with_factor,
  COUNT(*) - COUNT(unlock_factor_id) AS without_factor
FROM unlockables
GROUP BY type
ORDER BY type;
