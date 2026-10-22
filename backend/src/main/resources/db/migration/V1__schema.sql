CREATE TABLE horse (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(100) NOT NULL,
 sex VARCHAR(8) NOT NULL,
 birth_date DATE NOT NULL,
 color VARCHAR(40) NOT NULL,
 trainer VARCHAR(100) NOT NULL,
 sire_id BIGINT NULL,
 dam_id BIGINT NULL,
 CONSTRAINT fk_sire FOREIGN KEY(sire_id) REFERENCES horse(id),
 CONSTRAINT fk_dam FOREIGN KEY(dam_id) REFERENCES horse(id),
 INDEX ix_horse_name(name)
);
CREATE TABLE race (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(150) NOT NULL,
 race_date DATE NOT NULL,
 venue VARCHAR(100) NOT NULL,
 distance INT NOT NULL,
 surface VARCHAR(20) NOT NULL,
 INDEX ix_race_date(race_date), INDEX ix_race_name(name)
);
CREATE TABLE entry (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 race_id BIGINT NOT NULL,
 horse_id BIGINT NOT NULL,
 number INT NOT NULL,
 jockey VARCHAR(100) NOT NULL,
 finish_position INT NULL,
 time_seconds DECIMAL(7,2) NULL,
 CONSTRAINT fk_entry_race FOREIGN KEY(race_id) REFERENCES race(id),
 CONSTRAINT fk_entry_horse FOREIGN KEY(horse_id) REFERENCES horse(id),
 UNIQUE KEY uq_entry(race_id, horse_id),
 UNIQUE KEY uq_number(race_id, number),
 CONSTRAINT ck_finish CHECK (finish_position IS NULL OR finish_position > 0),
 CONSTRAINT ck_time CHECK (time_seconds IS NULL OR time_seconds > 0),
 INDEX ix_history(horse_id, race_id)
);
