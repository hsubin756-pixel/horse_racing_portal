package dev.keiba;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import io.jsonwebtoken.*;
import java.time.Instant;
import java.util.Date;
class JwtServiceTest {
 final JwtService jwt=new JwtService("test-only-key-never-use-in-production-12345678901234567890",1800);
 @Test void signedClaims() {var c=jwt.parse(jwt.create(7L));assertEquals("7",c.getSubject());assertNotNull(c.getId());assertEquals(1800,(c.getExpiration().getTime()-c.getIssuedAt().getTime())/1000);}
 @Test void rejectsExpired() {String t=Jwts.builder().issuer("keiba-field").subject("7").expiration(Date.from(Instant.now().minusSeconds(1))).signWith(jwt.key).compact();assertThrows(ExpiredJwtException.class,()->jwt.parse(t));}
 @Test void rejectsWrongKey() {var other=new JwtService("different-test-key-at-least-thirty-two-characters",1800);assertThrows(JwtException.class,()->other.parse(jwt.create(7L)));}
 @Test void refusesWeakConfig() {assertThrows(IllegalArgumentException.class,()->new JwtService("short",1800));}
 @Test void rejectsMissingAndInvalidClaims() {
  var now=Instant.now();
  for(int variant=0;variant<6;variant++) {
   var builder=Jwts.builder().issuer("keiba-field").signWith(jwt.key);
   if(variant!=0) builder.expiration(Date.from(now.plusSeconds(1800)));
   if(variant!=1) builder.issuedAt(Date.from(variant==5?now.plusSeconds(600):now));
   if(variant!=2) builder.id(variant==4?"bad-id":java.util.UUID.randomUUID().toString());
   if(variant!=3) builder.subject("7");
   String token=builder.compact();
   assertThrows(JwtException.class,()->jwt.parse(token));
  }
 }
}
