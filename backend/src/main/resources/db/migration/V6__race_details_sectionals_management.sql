ALTER TABLE race
 ADD start_time TIME NULL,
 ADD race_class VARCHAR(60) NULL,
 ADD weather VARCHAR(30) NULL,
 ADD going VARCHAR(30) NULL,
 ADD status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
 ADD source VARCHAR(120) NOT NULL DEFAULT 'synthetic_fixture',
 ADD revision BIGINT NOT NULL DEFAULT 0,
 ADD CONSTRAINT ck_race_status CHECK(status IN ('SCHEDULED','RUNNING','OFFICIAL','CANCELLED'));
UPDATE race SET status=CASE WHEN id<=7 THEN 'OFFICIAL' ELSE 'SCHEDULED' END,
 start_time='15:30:00',race_class='가상 오픈',weather='맑음',going='양호';
ALTER TABLE horse ADD revision BIGINT NOT NULL DEFAULT 0;
ALTER TABLE entry
 ADD gate INT NULL,
 ADD carried_weight DECIMAL(4,1) NULL,
 ADD body_weight INT NULL,
 ADD weight_change INT NULL,
 ADD status VARCHAR(20) NOT NULL DEFAULT 'DECLARED',
 ADD revision BIGINT NOT NULL DEFAULT 0,
 ADD CONSTRAINT ck_entry_state CHECK(status IN ('DECLARED','FINISHED','SCRATCHED','DNF','DISQUALIFIED')),
 ADD CONSTRAINT ck_entry_weights CHECK((gate IS NULL OR gate BETWEEN 1 AND 30) AND (carried_weight IS NULL OR carried_weight BETWEEN 30 AND 80) AND (body_weight IS NULL OR body_weight BETWEEN 200 AND 800) AND (weight_change IS NULL OR weight_change BETWEEN -100 AND 100));
UPDATE entry SET status=CASE WHEN finish_position IS NOT NULL THEN 'FINISHED' ELSE 'DECLARED' END,
 gate=number,carried_weight=54+MOD(number,4),body_weight=440+number*4,weight_change=MOD(number,5)*2-4;
ALTER TABLE member ADD is_admin BOOLEAN NOT NULL DEFAULT FALSE;
CREATE TABLE sectional (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 entry_id BIGINT NOT NULL,
 distance INT NOT NULL,
 position INT NULL,
 cumulative_seconds DECIMAL(7,2) NULL,
 source VARCHAR(120) NOT NULL,
 revision BIGINT NOT NULL DEFAULT 0,
 FOREIGN KEY(entry_id) REFERENCES entry(id),
 UNIQUE KEY uq_sectional(entry_id,distance),
 CHECK(distance>0),CHECK(position IS NULL OR position>0),
 CHECK(cumulative_seconds IS NULL OR cumulative_seconds>0),
 CHECK(position IS NOT NULL OR cumulative_seconds IS NOT NULL)
);
CREATE TABLE payout (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 race_id BIGINT NOT NULL,
 market VARCHAR(20) NOT NULL,
 combination VARCHAR(60) NOT NULL,
 status VARCHAR(20) NOT NULL,
 odds DECIMAL(10,1) NULL,
 amount_yen INT NULL,
 source VARCHAR(120) NOT NULL,
 as_of DATETIME(6) NOT NULL,
 revision BIGINT NOT NULL DEFAULT 0,
 FOREIGN KEY(race_id) REFERENCES race(id),
 UNIQUE KEY uq_payout(race_id,market,combination),
 CHECK(market IN ('WIN','PLACE','QUINELLA','EXACTA','TRIO','TRIFECTA')),
 CHECK(status IN ('OPEN','FINAL','REFUND')),
 CHECK((status='OPEN' AND odds>=1 AND amount_yen IS NULL) OR (status='FINAL' AND odds IS NULL AND amount_yen>=100) OR (status='REFUND' AND odds IS NULL AND amount_yen=100))
);
CREATE TABLE catalog_audit (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 member_id BIGINT NOT NULL,
 kind VARCHAR(20) NOT NULL,
 record_id BIGINT NOT NULL,
 before_json JSON NULL,
 after_json JSON NOT NULL,
 changed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY(member_id) REFERENCES member(id)
);
-- Fictional checkpoints. Intermediate positions are independent of final placing.
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,1,24.08,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,1,60.08,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,1,72.08,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,3,96.96,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,2,24.16,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,2,60.16,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,2,72.16,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,4,97.28,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,3,24.24,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,3,60.24,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,3,72.24,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,5,97.60,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,4,24.32,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,4,60.32,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,4,72.32,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,6,97.92,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,5,24.40,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,5,60.40,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,5,72.40,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,7,98.24,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,6,24.48,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,6,60.48,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,6,72.48,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,8,98.56,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,7,24.56,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,7,60.56,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,7,72.56,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,9,98.88,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,8,24.64,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,8,60.64,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,8,72.64,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,10,99.20,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,9,24.72,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,9,60.72,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,9,72.72,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,11,99.52,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,10,24.80,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,10,60.80,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,10,72.80,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,12,99.84,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,11,24.88,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,11,60.88,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,11,72.88,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,1,96.32,'synthetic_fixture' FROM entry WHERE race_id=1 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,1,24.08,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,2,84.16,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,2,96.16,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,4,123.28,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,2,24.16,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,3,84.24,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,3,96.24,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,5,123.60,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,3,24.24,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,4,84.32,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,4,96.32,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,6,123.92,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,4,24.32,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,5,84.40,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,5,96.40,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,7,124.24,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,5,24.40,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,6,84.48,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,6,96.48,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,8,124.56,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,6,24.48,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,7,84.56,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,7,96.56,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,9,124.88,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,7,24.56,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,8,84.64,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,8,96.64,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,10,125.20,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,8,24.64,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,9,84.72,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,9,96.72,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,11,125.52,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,9,24.72,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,10,84.80,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,10,96.80,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,12,125.84,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,10,24.80,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,11,84.88,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,11,96.88,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,1,122.32,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,11,24.88,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,12,84.96,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,12,96.96,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,2,122.64,'synthetic_fixture' FROM entry WHERE race_id=2 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,1,24.08,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,3,60.24,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,3,72.24,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,5,97.60,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,2,24.16,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,4,60.32,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,4,72.32,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,6,97.92,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,3,24.24,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,5,60.40,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,5,72.40,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,7,98.24,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,4,24.32,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,6,60.48,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,6,72.48,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,8,98.56,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,5,24.40,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,7,60.56,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,7,72.56,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,9,98.88,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,6,24.48,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,8,60.64,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,8,72.64,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,10,99.20,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,7,24.56,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,9,60.72,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,9,72.72,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,11,99.52,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,8,24.64,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,10,60.80,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,10,72.80,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,12,99.84,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,9,24.72,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,11,60.88,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,11,72.88,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,1,96.32,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,10,24.80,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,12,60.96,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,12,72.96,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,2,96.64,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,11,24.88,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,1,60.08,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,1,72.08,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,3,96.96,'synthetic_fixture' FROM entry WHERE race_id=3 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,1,24.08,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,4,84.32,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,4,96.32,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,6,123.92,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,2,24.16,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,5,84.40,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,5,96.40,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,7,124.24,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,3,24.24,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,6,84.48,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,6,96.48,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,8,124.56,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,4,24.32,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,7,84.56,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,7,96.56,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,9,124.88,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,5,24.40,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,8,84.64,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,8,96.64,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,10,125.20,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,6,24.48,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,9,84.72,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,9,96.72,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,11,125.52,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,7,24.56,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,10,84.80,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,10,96.80,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,12,125.84,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,8,24.64,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,11,84.88,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,11,96.88,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,1,122.32,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,9,24.72,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,12,84.96,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,12,96.96,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,2,122.64,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,10,24.80,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,1,84.08,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,1,96.08,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,3,122.96,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,11,24.88,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,2,84.16,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,2,96.16,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,4,123.28,'synthetic_fixture' FROM entry WHERE race_id=4 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,1,24.08,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,5,60.40,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,5,72.40,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,7,98.24,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,2,24.16,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,6,60.48,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,6,72.48,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,8,98.56,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,3,24.24,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,7,60.56,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,7,72.56,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,9,98.88,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,4,24.32,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,8,60.64,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,8,72.64,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,10,99.20,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,5,24.40,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,9,60.72,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,9,72.72,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,11,99.52,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,6,24.48,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,10,60.80,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,10,72.80,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,12,99.84,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,7,24.56,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,11,60.88,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,11,72.88,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,1,96.32,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,8,24.64,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,12,60.96,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,12,72.96,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,2,96.64,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,9,24.72,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,1,60.08,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,1,72.08,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,3,96.96,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,10,24.80,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,2,60.16,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,2,72.16,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,4,97.28,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,11,24.88,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,3,60.24,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,3,72.24,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,5,97.60,'synthetic_fixture' FROM entry WHERE race_id=5 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,1,24.08,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,6,84.48,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,6,96.48,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,8,124.56,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,2,24.16,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,7,84.56,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,7,96.56,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,9,124.88,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,3,24.24,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,8,84.64,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,8,96.64,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,10,125.20,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,4,24.32,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,9,84.72,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,9,96.72,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,11,125.52,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,5,24.40,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,10,84.80,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,10,96.80,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,12,125.84,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,6,24.48,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,11,84.88,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,11,96.88,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,1,122.32,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,7,24.56,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,12,84.96,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,12,96.96,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,2,122.64,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,8,24.64,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,1,84.08,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,1,96.08,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,3,122.96,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,9,24.72,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,2,84.16,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,2,96.16,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,4,123.28,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,10,24.80,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,3,84.24,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,3,96.24,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,5,123.60,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,11,24.88,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1400,4,84.32,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,4,96.32,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,2000,6,123.92,'synthetic_fixture' FROM entry WHERE race_id=6 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,1,24.08,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,7,60.56,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,7,72.56,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,9,98.88,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=1;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,2,24.16,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,8,60.64,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,8,72.64,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,10,99.20,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=2;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,3,24.24,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,9,60.72,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,9,72.72,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,11,99.52,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=3;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,4,24.32,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,10,60.80,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,10,72.80,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,12,99.84,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=4;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,5,24.40,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,11,60.88,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,11,72.88,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,1,96.32,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=5;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,6,24.48,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,12,60.96,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,12,72.96,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,2,96.64,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=6;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,7,24.56,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,1,60.08,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,1,72.08,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,3,96.96,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=7;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,8,24.64,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,2,60.16,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,2,72.16,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,4,97.28,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=8;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,9,24.72,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,3,60.24,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,3,72.24,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,5,97.60,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=9;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,10,24.80,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,4,60.32,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,4,72.32,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,6,97.92,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=10;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,400,11,24.88,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1000,5,60.40,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1200,5,72.40,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=11;
INSERT INTO sectional(entry_id,distance,position,cumulative_seconds,source) SELECT id,1600,7,98.24,'synthetic_fixture' FROM entry WHERE race_id=7 AND number=11;
INSERT INTO payout(race_id,market,combination,status,amount_yen,source,as_of) VALUES
 (1,'WIN','11','FINAL',560,'synthetic_fixture','2025-01-15 06:40:00'),
 (1,'QUINELLA','11-12','FINAL',1840,'synthetic_fixture','2025-01-15 06:40:00'),
 (1,'EXACTA','11-12','FINAL',3250,'synthetic_fixture','2025-01-15 06:40:00'),
 (1,'TRIO','1-11-12','FINAL',4620,'synthetic_fixture','2025-01-15 06:40:00'),
 (1,'TRIFECTA','11-12-1','FINAL',13870,'synthetic_fixture','2025-01-15 06:40:00');
INSERT INTO payout(race_id,market,combination,status,odds,source,as_of) VALUES
 (8,'QUINELLA','1-11','OPEN',18.4,'synthetic_fixture','2026-10-22 03:00:00');
