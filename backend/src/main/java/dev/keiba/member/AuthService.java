package dev.keiba.member;

import dev.keiba.common.ApiException;
import dev.keiba.security.JwtService;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
class AuthService {

    private final MemberRepository members;
    private final BCryptPasswordEncoder encoder;
    private final JwtService jwt;
    private final RevokedTokenRepository revoked;
    // A hash with the same cost avoids an obvious unknown-email timing shortcut.
    private final String dummyHash;

    AuthService(
        MemberRepository members,
        BCryptPasswordEncoder encoder,
        JwtService jwt,
        RevokedTokenRepository revoked
    ) {
        this.members = members;
        this.encoder = encoder;
        this.jwt = jwt;
        this.revoked = revoked;
        this.dummyHash = encoder.encode(java.util.UUID.randomUUID().toString());
    }

    record LoginResult(String token, String nickname, long expiresIn) {}

    void register(AuthController.Register input) {
        String email = input.email().strip().toLowerCase(Locale.ROOT),
            nickname = input.nickname().strip();
        if (nickname.isEmpty() || input.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new ApiException(400, "닉네임 또는 비밀번호 길이를 확인하세요.");
        }
        if (members.existsByEmail(email)) {
            throw new ApiException(409, "이미 가입된 이메일입니다.");
        }
        members.saveAndFlush(new Member(email, encoder.encode(input.password()), nickname));
    }

    @Transactional(readOnly = true)
    LoginResult login(AuthController.Login input) {
        if (input.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new ApiException(401, "이메일 또는 비밀번호가 올바르지 않습니다.");
        }
        var found = members.findByEmail(input.email().strip().toLowerCase(Locale.ROOT));
        // 없는 이메일이어도 같은 비용의 해시 비교를 수행해 응답 시간으로 가입 여부를 추측하기 어렵게 합니다.
        boolean matches = encoder.matches(input.password(), found.map(m -> m.passwordHash).orElse(dummyHash));
        if (!matches || found.isEmpty()) {
            throw new ApiException(401, "이메일 또는 비밀번호가 올바르지 않습니다.");
        }
        Member member = found.get();
        return new LoginResult(jwt.create(member.id), member.nickname, jwt.ttlSeconds());
    }

    void logout(String authorization) {
        var claims = jwt.parse(authorization.substring("Bearer ".length()));
        revoked.save(new RevokedToken(claims.getId(), claims.getExpiration().toInstant()));
    }
}
