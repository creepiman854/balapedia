-- =============================================================================
-- Seed del catálogo unlock_factors
-- =============================================================================
-- Inserta los 31 factores de desbloqueo del juego (uno por achievement no
-- PlayStation). Idempotente: usa INSERT IGNORE contra el UNIQUE(code), por
-- lo que se puede re-ejecutar sin riesgo de duplicados ni de error.
--
-- Convención de naming para `code`: SCREAMING_SNAKE_CASE, verbo en infinitivo
-- seguido del objeto/condición. Ej: REACH_ANTE_4, WIN_RUN, DISCOVER_ALL_TAROTS.
-- Los `code` son identificadores estables usados por los resolvers de
-- auto-unlock, así que NO se renombran sin migración acompañante.
--
-- Las descripciones siguen literalmente la wiki de Balatro para que la UI
-- pueda mostrarlas tal cual sin transformación adicional.
-- =============================================================================

INSERT IGNORE INTO unlock_factors (code, description) VALUES
  ('REACH_ANTE_4',                'Reach Ante 4.'),
  ('REACH_ANTE_8',                'Reach Ante 8.'),
  ('WIN_RUN',                     'Win a Run.'),
  ('WIN_RED_STAKE',               'Win a run on at least Red Stake difficulty.'),
  ('WIN_BLACK_STAKE',             'Win a run on at least Black Stake difficulty.'),
  ('WIN_GOLD_STAKE',              'Win a run on at least Gold Stake difficulty.'),
  ('PLAY_2500_CARDS',             'Play at least 2500 Cards.'),
  ('DISCARD_2500_CARDS',          'Discard at least 2500 Cards.'),
  ('HAVE_400_MONEY',              'Have $400 or more during a single run.'),
  ('PLAY_FLUSH_5_WILD',           'Play a Flush with 5 Wild cards.'),
  ('WIN_12_OR_FEWER_ROUNDS',      'Win a run in 12 or fewer rounds.'),
  ('BUY_5_VOUCHERS_BY_ANTE_4',    'Buy 5 vouchers by Ante 4.'),
  ('BREAK_2_GLASS_SINGLE_HAND',   'Break 2 Glass cards in a single hand.'),
  ('PLAY_ROYAL_FLUSH',            'Play a Royal Flush.'),
  ('HAND_LEVEL_10',               'Get any poker hand to level 10.'),
  ('SCORE_10K_SINGLE_HAND',       'Score 10,000 Chips in a single hand.'),
  ('SCORE_1M_SINGLE_HAND',        'Score 1,000,000 Chips in a single hand.'),
  ('SCORE_100M_SINGLE_HAND',      'Score 100,000,000 Chips in a single hand.'),
  ('DECK_20_OR_FEWER_CARDS',      'Thin your deck down to 20 or fewer cards.'),
  ('DECK_80_OR_MORE_CARDS',       'Have 80 or more cards in your deck.'),
  ('WIN_WITHOUT_REROLL_SHOP',     'Win a run without rerolling the shop.'),
  ('COMPLETE_ANY_CHALLENGE',      'Complete any challenge run.'),
  ('COMPLETE_ALL_CHALLENGES',     'Complete every challenge run.'),
  ('DISCOVER_LEGENDARY_JOKER',    'Discover a Legendary Joker.'),
  ('DISCOVER_ALL_PLANETS',        'Discover every Planet card.'),
  ('DISCOVER_ALL_TAROTS',         'Discover every Tarot card.'),
  ('DISCOVER_ALL_SPECTRALS',      'Discover every Spectral card.'),
  ('DISCOVER_ALL_VOUCHERS',       'Discover every Voucher.'),
  ('DISCOVER_100_PERCENT',        'Discover 100% of your collection.'),
  ('WIN_ALL_DECKS_GOLD_STAKE',    'Win with every deck at Gold Stake difficulty.'),
  ('GOLD_STICKER_ALL_JOKERS',     'Earn a Gold Sticker on every Joker.');

-- Verificación: debería devolver 31 filas
SELECT COUNT(*) AS total_factors FROM unlock_factors;
SELECT code, description FROM unlock_factors ORDER BY id;
