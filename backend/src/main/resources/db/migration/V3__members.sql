CREATE TABLE member (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 email VARCHAR(254) NOT NULL,
 password_hash VARCHAR(100) NOT NULL,
 nickname VARCHAR(40) NOT NULL,
 UNIQUE KEY uq_email(email)
);
CREATE TABLE favorite (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 member_id BIGINT NOT NULL,
 horse_id BIGINT NOT NULL,
 CONSTRAINT fk_favorite_member FOREIGN KEY(member_id) REFERENCES member(id),
 CONSTRAINT fk_favorite_horse FOREIGN KEY(horse_id) REFERENCES horse(id),
 UNIQUE KEY uq_favorite(member_id,horse_id)
);
CREATE TABLE revoked_token (
 jti VARCHAR(36) PRIMARY KEY,
 expires_at DATETIME(6) NOT NULL,
 INDEX ix_revoked_expiry(expires_at)
);
