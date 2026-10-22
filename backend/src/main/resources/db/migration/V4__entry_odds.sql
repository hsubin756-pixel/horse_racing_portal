-- One win-odds snapshot per starter. Existing migrations and user data stay intact.
ALTER TABLE entry
 ADD COLUMN popularity_rank INT NULL,
 ADD COLUMN win_odds DECIMAL(7,1) NULL,
 ADD COLUMN odds_source VARCHAR(40) NULL,
 ADD COLUMN odds_as_of DATETIME(6) NULL,
 ADD CONSTRAINT ck_popularity CHECK (popularity_rank IS NULL OR popularity_rank > 0),
 ADD CONSTRAINT ck_win_odds CHECK (win_odds IS NULL OR win_odds >= 1.0),
 ADD CONSTRAINT ck_odds_snapshot CHECK (
  (popularity_rank IS NULL AND win_odds IS NULL AND odds_source IS NULL AND odds_as_of IS NULL)
  OR
  (popularity_rank IS NOT NULL AND win_odds IS NOT NULL AND odds_source IS NOT NULL
   AND CHAR_LENGTH(TRIM(odds_source)) > 0 AND odds_as_of IS NOT NULL)
 );

-- Fictional values: independent of finish_position and the experimental ML scores.
-- 5 is coprime to the 12-starter fixture field: each race receives ranks 1..12.
UPDATE entry e JOIN race r ON r.id = e.race_id
 SET e.popularity_rank = MOD((e.number - 1) * 5 + e.race_id * 3, 12) + 1,
 e.win_odds = CASE MOD((e.number - 1) * 5 + e.race_id * 3, 12) + 1
  WHEN 1 THEN 2.4 WHEN 2 THEN 3.8 WHEN 3 THEN 5.6 WHEN 4 THEN 7.2
  WHEN 5 THEN 9.9 WHEN 6 THEN 12.5 WHEN 7 THEN 16.0 WHEN 8 THEN 22.3
  WHEN 9 THEN 31.0 WHEN 10 THEN 46.7 WHEN 11 THEN 68.0 WHEN 12 THEN 99.9 END,
 e.odds_source = 'synthetic_fixture',
 e.odds_as_of = TIMESTAMP(LEAST(r.race_date, '2026-10-22'), '03:00:00')
 WHERE e.race_id BETWEEN 1 AND 8 AND e.horse_id BETWEEN 22 AND 33 AND e.number BETWEEN 1 AND 12;

-- One missing snapshot in the upcoming fixture exercises the unavailable UI state.
UPDATE entry SET popularity_rank = NULL, win_odds = NULL, odds_source = NULL, odds_as_of = NULL
 WHERE race_id = 8 AND popularity_rank = 12;
