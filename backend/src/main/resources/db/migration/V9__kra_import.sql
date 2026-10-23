-- Provider identifiers are separate from local IDs and preserve leading zeroes.
ALTER TABLE horse ADD kra_id VARCHAR(16) NULL, ADD UNIQUE KEY uq_horse_kra(kra_id);
ALTER TABLE person ADD kra_id VARCHAR(16) NULL, ADD UNIQUE KEY uq_person_kra(kind,kra_id);
ALTER TABLE race ADD kra_id VARCHAR(40) NULL, ADD UNIQUE KEY uq_race_kra(kra_id);
ALTER TABLE entry
 ADD trainer_id BIGINT NULL, ADD trainer_name VARCHAR(100) NULL,
 ADD FOREIGN KEY(trainer_id) REFERENCES person(id),
 DROP CHECK ck_odds_snapshot,
 ADD CONSTRAINT ck_odds_snapshot CHECK (
  (popularity_rank IS NULL AND win_odds IS NULL AND odds_source IS NULL AND odds_as_of IS NULL)
  OR ((popularity_rank IS NOT NULL OR win_odds IS NOT NULL) AND odds_source IS NOT NULL
      AND CHAR_LENGTH(TRIM(odds_source)) > 0 AND odds_as_of IS NOT NULL)
 );
CREATE TABLE sectional_marker (
 entry_id BIGINT NOT NULL,
 marker INT NOT NULL,
 position INT NULL,
 cumulative_seconds DECIMAL(7,2) NULL,
 source VARCHAR(120) NOT NULL,
 PRIMARY KEY(entry_id,marker),
 FOREIGN KEY(entry_id) REFERENCES entry(id),
 CHECK(marker BETWEEN 1 AND 4),
 CHECK(position IS NULL OR position>0),
 CHECK(cumulative_seconds IS NULL OR cumulative_seconds>0),
 CHECK(position IS NOT NULL OR cumulative_seconds IS NOT NULL)
);
CREATE TABLE kra_race_import (
 race_id BIGINT PRIMARY KEY,
 fingerprint CHAR(64) NOT NULL,
 raw_json JSON NOT NULL,
 retrieved_at DATETIME(6) NOT NULL,
 imported_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY(race_id) REFERENCES race(id)
);
