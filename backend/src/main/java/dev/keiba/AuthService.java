package dev.keiba;
import java.util.Locale;
import java.nio.charset.StandardCharsets;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
@Service @Transactional
class AuthService {
 final MemberRepository members; final BCryptPasswordEncoder encoder; final JwtService jwt; final RevokedTokenRepository revoked;
 // A hash with the same cost avoids an obvious unknown-email timing shortcut.
 final String dummyHash;
 AuthService(MemberRepository m,BCryptPasswordEncoder e,JwtService j,RevokedTokenRepository r) {members=m;encoder=e;jwt=j;revoked=r;dummyHash=e.encode(java.util.UUID.randomUUID().toString());}
 record LoginResult(String token,String nickname,long expiresIn) {}
 void register(AuthController.Register input) {
  String email=input.email().strip().toLowerCase(Locale.ROOT), nickname=input.nickname().strip();
  if(nickname.isEmpty() || input.password().getBytes(StandardCharsets.UTF_8).length>72) throw new ApiException(400,"닉네임 또는 비밀번호 길이를 확인하세요.");
  if(members.existsByEmail(email)) throw new ApiException(409,"이미 가입된 이메일입니다.");
  members.saveAndFlush(new Member(email,encoder.encode(input.password()),nickname));
 }
 @Transactional(readOnly=true) LoginResult login(AuthController.Login input) {
  if(input.password().getBytes(StandardCharsets.UTF_8).length>72) throw new ApiException(401,"이메일 또는 비밀번호가 올바르지 않습니다.");
  var m=members.findByEmail(input.email().strip().toLowerCase(Locale.ROOT));
  boolean ok=encoder.matches(input.password(),m.map(x->x.passwordHash).orElse(dummyHash));
  if(!ok || m.isEmpty()) throw new ApiException(401,"이메일 또는 비밀번호가 올바르지 않습니다.");
  Member member=m.get();return new LoginResult(jwt.create(member.id),member.nickname,jwt.ttl);
 }
 void logout(String authorization) { var c=jwt.parse(authorization.substring(7));revoked.save(new RevokedToken(c.getId(),c.getExpiration().toInstant())); }
}
