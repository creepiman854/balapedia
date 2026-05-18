-- =============================================================================
-- Normalización del texto `unlock_condition` legacy en unlockables
-- =============================================================================
-- Alinea las descripciones de los 14 items con shared unlock a la redacción
-- canónica del wiki de Balatro (la misma que está en unlock_factors.description
-- para los achievements correspondientes).
--
-- Motivación: antes de esta rama las descripciones se cargaban de scrapes con
-- formatos heterogéneos ("Reach Ante level 4" vs "Reach Ante 4", "In one
-- hand, earn at least 10,000 chips" vs "Score 10,000 Chips in a single hand",
-- mayúsculas inconsistentes en "Card/card", etc.). Tras esta normalización,
-- el campo `unlock_condition` y la descripción del `unlock_factor` asociado
-- son idénticos para los 14 items con shared unlock.
--
-- Casos especiales corregidos:
--   - Astronomer: "Discover every card" (estaba mal — faltaba "Planet")
--   - Cartomancer: "Card" → "card" (consistencia con resto del wiki)
--   - Stuntman: simplificación de "100 million (100,000,000)" a "100,000,000"
--
-- Idempotente. Re-ejecutar deja el mismo texto.
-- =============================================================================

-- ---- JOKERS ------------------------------------------------------------------
UPDATE unlockables SET unlock_condition = 'Reach Ante 4.'                                 WHERE type = 'JOKER' AND name = 'Showman';
UPDATE unlockables SET unlock_condition = 'Reach Ante 8.'                                 WHERE type = 'JOKER' AND name = 'Flower Pot';
UPDATE unlockables SET unlock_condition = 'Win a Run.'                                    WHERE type = 'JOKER' AND name = 'Blueprint';
UPDATE unlockables SET unlock_condition = 'Have $400 or more during a single run.'        WHERE type = 'JOKER' AND name = 'Satellite';
UPDATE unlockables SET unlock_condition = 'Win a run in 12 or fewer rounds.'              WHERE type = 'JOKER' AND name = 'Merry Andy';
UPDATE unlockables SET unlock_condition = 'Score 10,000 Chips in a single hand.'          WHERE type = 'JOKER' AND name = 'Oops! All 6s';
UPDATE unlockables SET unlock_condition = 'Score 1,000,000 Chips in a single hand.'       WHERE type = 'JOKER' AND name = 'The Idol';
UPDATE unlockables SET unlock_condition = 'Score 100,000,000 Chips in a single hand.'     WHERE type = 'JOKER' AND name = 'Stuntman';
UPDATE unlockables SET unlock_condition = 'Discover every Planet card.'                   WHERE type = 'JOKER' AND name = 'Astronomer';
UPDATE unlockables SET unlock_condition = 'Discover every Tarot card.'                    WHERE type = 'JOKER' AND name = 'Cartomancer';

-- ---- VOUCHERS ----------------------------------------------------------------
UPDATE unlockables SET unlock_condition = 'Play at least 2500 Cards.'                     WHERE type = 'VOUCHER' AND name = 'Nacho Tong';
UPDATE unlockables SET unlock_condition = 'Discard at least 2500 Cards.'                  WHERE type = 'VOUCHER' AND name = 'Recyclomancy';

-- ---- DECKS -------------------------------------------------------------------
UPDATE unlockables SET unlock_condition = 'Win a run on at least Red Stake difficulty.'   WHERE type = 'DECK' AND name = 'Zodiac Deck';
UPDATE unlockables SET unlock_condition = 'Win a run on at least Black Stake difficulty.' WHERE type = 'DECK' AND name = 'Anaglyph Deck';

-- =============================================================================
-- Verificación: los 14 items con factor enlazado deben tener su
-- unlock_condition igual a la descripción del factor (excepto signos de
-- puntuación menores si los hubiera, que aquí ya están alineados).
-- =============================================================================
SELECT
  u.type,
  u.name,
  u.unlock_condition,
  uf.description AS factor_description,
  CASE
    WHEN u.unlock_condition = uf.description THEN 'OK'
    ELSE 'MISMATCH'
  END AS check_status
FROM unlockables u
JOIN unlock_factors uf ON uf.id = u.unlock_factor_id
ORDER BY u.type, u.name;
