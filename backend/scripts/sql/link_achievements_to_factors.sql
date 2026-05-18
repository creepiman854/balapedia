-- =============================================================================
-- Enlazar cada achievement existente con su unlock_factor correspondiente
-- =============================================================================
-- Mapea los 31 achievements (BAL_01..BAL_31) a su condición de desbloqueo
-- canónica en la tabla unlock_factors, vía la nueva columna unlock_factor_id.
--
-- Idempotente: el UPDATE deja la columna en el mismo valor si ya estaba
-- enlazada. Re-ejecutar es seguro y no afecta otras columnas.
--
-- El matching se hace por steam_api_name (estable) y no por nombre (que podría
-- traducirse o cambiar). Cada UPDATE incluye en el WHERE el subselect del
-- factor en lugar de un id hardcoded, para no depender del orden en que se
-- corrió el seed de unlock_factors.
-- =============================================================================

UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'REACH_ANTE_4')               WHERE steam_api_name = 'BAL_01';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'REACH_ANTE_8')               WHERE steam_api_name = 'BAL_02';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_RUN')                    WHERE steam_api_name = 'BAL_03';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_RED_STAKE')              WHERE steam_api_name = 'BAL_04';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_BLACK_STAKE')            WHERE steam_api_name = 'BAL_05';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_GOLD_STAKE')             WHERE steam_api_name = 'BAL_06';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'PLAY_2500_CARDS')            WHERE steam_api_name = 'BAL_07';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCARD_2500_CARDS')         WHERE steam_api_name = 'BAL_08';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'HAVE_400_MONEY')             WHERE steam_api_name = 'BAL_09';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'PLAY_FLUSH_5_WILD')          WHERE steam_api_name = 'BAL_10';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_12_OR_FEWER_ROUNDS')     WHERE steam_api_name = 'BAL_11';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'BUY_5_VOUCHERS_BY_ANTE_4')   WHERE steam_api_name = 'BAL_12';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'BREAK_2_GLASS_SINGLE_HAND')  WHERE steam_api_name = 'BAL_13';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'PLAY_ROYAL_FLUSH')           WHERE steam_api_name = 'BAL_14';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'HAND_LEVEL_10')              WHERE steam_api_name = 'BAL_15';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'SCORE_10K_SINGLE_HAND')      WHERE steam_api_name = 'BAL_16';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'SCORE_1M_SINGLE_HAND')       WHERE steam_api_name = 'BAL_17';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'SCORE_100M_SINGLE_HAND')     WHERE steam_api_name = 'BAL_18';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DECK_20_OR_FEWER_CARDS')     WHERE steam_api_name = 'BAL_19';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DECK_80_OR_MORE_CARDS')      WHERE steam_api_name = 'BAL_20';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_WITHOUT_REROLL_SHOP')    WHERE steam_api_name = 'BAL_21';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'COMPLETE_ANY_CHALLENGE')     WHERE steam_api_name = 'BAL_22';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'COMPLETE_ALL_CHALLENGES')    WHERE steam_api_name = 'BAL_23';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_LEGENDARY_JOKER')   WHERE steam_api_name = 'BAL_24';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_ALL_PLANETS')       WHERE steam_api_name = 'BAL_25';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_ALL_TAROTS')        WHERE steam_api_name = 'BAL_26';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_ALL_SPECTRALS')     WHERE steam_api_name = 'BAL_27';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_ALL_VOUCHERS')      WHERE steam_api_name = 'BAL_28';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'DISCOVER_100_PERCENT')       WHERE steam_api_name = 'BAL_29';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'WIN_ALL_DECKS_GOLD_STAKE')   WHERE steam_api_name = 'BAL_30';
UPDATE achievements SET unlock_factor_id = (SELECT id FROM unlock_factors WHERE code = 'GOLD_STICKER_ALL_JOKERS')    WHERE steam_api_name = 'BAL_31';

-- Verificación: los 31 achievements deben tener unlock_factor_id NOT NULL
SELECT
  COUNT(*)                                  AS total_achievements,
  COUNT(unlock_factor_id)                   AS linked,
  COUNT(*) - COUNT(unlock_factor_id)        AS unlinked
FROM achievements;

-- Listado completo del mapeo final
SELECT
  a.steam_api_name,
  a.name           AS achievement,
  uf.code          AS factor_code,
  uf.description   AS factor_description
FROM achievements a
LEFT JOIN unlock_factors uf ON uf.id = a.unlock_factor_id
ORDER BY a.id;
