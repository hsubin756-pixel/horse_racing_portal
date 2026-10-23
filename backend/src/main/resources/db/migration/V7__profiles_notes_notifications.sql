CREATE TABLE person (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 kind VARCHAR(10) NOT NULL,
 name VARCHAR(100) NOT NULL,
 biography VARCHAR(2000) NOT NULL DEFAULT '',
 source VARCHAR(120) NOT NULL DEFAULT 'synthetic_fixture',
 revision BIGINT NOT NULL DEFAULT 0,
 CHECK(kind IN ('JOCKEY','TRAINER')),
 INDEX ix_person_name(name)
);
INSERT INTO person(kind,name) SELECT DISTINCT 'JOCKEY',jockey FROM entry;
INSERT INTO person(kind,name) SELECT DISTINCT 'TRAINER',trainer FROM horse;
ALTER TABLE horse ADD trainer_id BIGINT NULL,ADD FOREIGN KEY(trainer_id) REFERENCES person(id);
ALTER TABLE entry ADD jockey_id BIGINT NULL,ADD FOREIGN KEY(jockey_id) REFERENCES person(id);
UPDATE horse h JOIN person p ON p.name=h.trainer AND p.kind='TRAINER' SET h.trainer_id=p.id;
UPDATE entry e JOIN person p ON p.name=e.jockey AND p.kind='JOCKEY' SET e.jockey_id=p.id;
CREATE TABLE personal_note (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 member_id BIGINT NOT NULL,
 horse_id BIGINT NULL,
 race_id BIGINT NULL,
 body VARCHAR(2000) NOT NULL,
 tags VARCHAR(200) NOT NULL DEFAULT '',
 revision BIGINT NOT NULL DEFAULT 0,
 updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY(member_id) REFERENCES member(id),
 FOREIGN KEY(horse_id) REFERENCES horse(id),
 FOREIGN KEY(race_id) REFERENCES race(id),
 CHECK((horse_id IS NULL)<>(race_id IS NULL)),
 UNIQUE KEY uq_note_horse(member_id,horse_id),
 UNIQUE KEY uq_note_race(member_id,race_id)
);
CREATE TABLE site_notification (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 member_id BIGINT NOT NULL,
 race_id BIGINT NOT NULL,
 race_date DATE NOT NULL,
 message VARCHAR(300) NOT NULL,
 is_read BOOLEAN NOT NULL DEFAULT FALSE,
 created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
 FOREIGN KEY(member_id) REFERENCES member(id),
 FOREIGN KEY(race_id) REFERENCES race(id),
 UNIQUE KEY uq_notification(member_id,race_id,race_date)
);
