CREATE TABLE race_favorite (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 member_id BIGINT NOT NULL,
 race_id BIGINT NOT NULL,
 CONSTRAINT fk_race_favorite_member FOREIGN KEY(member_id) REFERENCES member(id),
 CONSTRAINT fk_race_favorite_race FOREIGN KEY(race_id) REFERENCES race(id),
 UNIQUE KEY uq_member_race(member_id,race_id)
);
