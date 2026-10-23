-- Master data from the approved KRA open APIs: horse profiles, name-only ancestors, people profiles, planned races.
-- Name-only ancestors from the pedigree API have no birth date; nothing is fabricated.
ALTER TABLE horse
 MODIFY birth_date DATE NULL,
 ADD source VARCHAR(120) NOT NULL DEFAULT 'synthetic_fixture',
 ADD name_en VARCHAR(100) NULL,
 ADD origin VARCHAR(40) NULL,
 ADD breed VARCHAR(40) NULL,
 ADD kra_rank VARCHAR(20) NULL,
 ADD owner_name VARCHAR(100) NULL,
 ADD ancestor_key VARCHAR(140) NULL,
 ADD profile_json JSON NULL,
 ADD profile_as_of DATETIME(6) NULL,
 ADD UNIQUE KEY uq_horse_ancestor(ancestor_key),
 ADD CONSTRAINT ck_horse_ancestor CHECK (ancestor_key IS NULL OR kra_id IS NULL);
UPDATE horse SET source='KRA_API214_1' WHERE kra_id IS NOT NULL;
ALTER TABLE person
 ADD debut_date DATE NULL,
 ADD retired_date DATE NULL,
 ADD affiliation VARCHAR(60) NULL,
 ADD profile_json JSON NULL,
 ADD profile_as_of DATETIME(6) NULL;
ALTER TABLE race ADD prize_json JSON NULL;
CREATE TABLE kra_master_import (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 kind VARCHAR(20) NOT NULL,
 subject VARCHAR(60) NOT NULL,
 fingerprint CHAR(64) NOT NULL,
 raw_json JSON NOT NULL,
 retrieved_at DATETIME(6) NOT NULL,
 imported_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 UNIQUE KEY uq_master(kind,subject),
 CHECK(kind IN ('HORSE','PEDIGREE','JOCKEY','TRAINER','PLAN'))
);
