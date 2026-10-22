package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="revoked_token")
class RevokedToken {
 @Id String jti;
 java.time.Instant expiresAt;
 protected RevokedToken() {}
 RevokedToken(String jti,java.time.Instant expiresAt) { this.jti=jti;this.expiresAt=expiresAt; }
}
