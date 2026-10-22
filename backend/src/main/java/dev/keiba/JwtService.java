package dev.keiba;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
@Service
class JwtService {
 final SecretKey key; final long ttl;
 JwtService(@Value("${app.jwt-secret}") String secret,@Value("${app.jwt-ttl-seconds}") long ttl) {
  if(secret.getBytes(StandardCharsets.UTF_8).length<32 || ttl<1 || ttl>86400) throw new IllegalArgumentException("JWT key must be at least 32 bytes; TTL 1..86400 seconds");
  key=Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));this.ttl=ttl;
 }
 String create(Long id) { var now=Instant.now(); return Jwts.builder().issuer("keiba-field").subject(id.toString()).id(UUID.randomUUID().toString()).issuedAt(Date.from(now)).expiration(Date.from(now.plusSeconds(ttl))).signWith(key).compact(); }
 Claims parse(String token) { return Jwts.parser().verifyWith(key).requireIssuer("keiba-field").build().parseSignedClaims(token).getPayload(); }
}
