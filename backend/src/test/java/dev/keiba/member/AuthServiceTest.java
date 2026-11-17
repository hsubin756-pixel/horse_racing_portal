package dev.keiba.member;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import dev.keiba.common.ApiException;
import dev.keiba.security.JwtService;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/** 회원가입·로그인·로그아웃 규칙을 DB 없이 검증합니다(리포지토리는 Mockito 대역). */
class AuthServiceTest {

    static final String SECRET = "test-only-key-never-use-in-production-12345678901234567890";
    MemberRepository members;
    RevokedTokenRepository revoked;
    JwtService jwt;
    AuthService service;
    // 운영 비용 12 대신 4를 써서 테스트 속도만 줄입니다. 해시 형식은 같습니다.
    final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(4);

    @BeforeEach
    void setUp() {
        members = mock(MemberRepository.class);
        revoked = mock(RevokedTokenRepository.class);
        jwt = new JwtService(SECRET, 1800);
        service = new AuthService(members, encoder, jwt, revoked);
    }

    Member saved(String email, String password, String nickname, long id) {
        var member = new Member(email, encoder.encode(password), nickname);
        member.id = id;
        return member;
    }

    @Test
    void registerNormalizesEmailAndStoresOnlyBcryptHash() {
        service.register(new AuthController.Register("  Rider@Example.COM ", "correct-horse-1", " 기수 "));
        var captor = ArgumentCaptor.forClass(Member.class);
        verify(members).saveAndFlush(captor.capture());
        Member member = captor.getValue();
        assertEquals("rider@example.com", member.email);
        assertEquals("기수", member.nickname);
        assertNotEquals("correct-horse-1", member.passwordHash);
        assertTrue(member.passwordHash.startsWith("$2"), "BCrypt 해시여야 합니다");
        assertTrue(encoder.matches("correct-horse-1", member.passwordHash));
    }

    @Test
    void registerRejectsDuplicateEmailWith409() {
        when(members.existsByEmail("dup@example.com")).thenReturn(true);
        var error = assertThrows(ApiException.class, () ->
            service.register(new AuthController.Register("dup@example.com", "correct-horse-1", "nick"))
        );
        assertEquals(409, error.status());
        verify(members, never()).saveAndFlush(any());
    }

    @Test
    void registerRejectsPasswordLongerThan72Bytes() {
        // 한글 25자 = 75바이트. BCrypt는 72바이트 이후를 무시하므로 거부해야 합니다.
        var error = assertThrows(ApiException.class, () ->
            service.register(new AuthController.Register("a@example.com", "가".repeat(25), "nick"))
        );
        assertEquals(400, error.status());
    }

    @Test
    void loginReturnsSignedTokenForMemberId() {
        when(members.findByEmail("rider@example.com")).thenReturn(
            Optional.of(saved("rider@example.com", "correct-horse-1", "기수", 42L))
        );
        var result = service.login(new AuthController.Login(" Rider@example.com", "correct-horse-1"));
        assertEquals("기수", result.nickname());
        assertEquals(1800, result.expiresIn());
        assertEquals("42", jwt.parse(result.token()).getSubject());
    }

    @Test
    void loginUsesSameErrorForWrongPasswordAndUnknownEmail() {
        when(members.findByEmail("rider@example.com")).thenReturn(
            Optional.of(saved("rider@example.com", "correct-horse-1", "기수", 42L))
        );
        when(members.findByEmail("nobody@example.com")).thenReturn(Optional.empty());
        var wrong = assertThrows(ApiException.class, () ->
            service.login(new AuthController.Login("rider@example.com", "wrong-password"))
        );
        var unknown = assertThrows(ApiException.class, () ->
            service.login(new AuthController.Login("nobody@example.com", "whatever-pass"))
        );
        assertEquals(401, wrong.status());
        assertEquals(401, unknown.status());
        assertEquals(wrong.getMessage(), unknown.getMessage(), "가입 여부를 응답으로 알 수 없어야 합니다");
    }

    @Test
    void logoutStoresTokenIdUntilItsExpiry() {
        String token = jwt.create(42L);
        var claims = jwt.parse(token);
        service.logout("Bearer " + token);
        var captor = ArgumentCaptor.forClass(RevokedToken.class);
        verify(revoked).save(captor.capture());
        assertEquals(claims.getId(), captor.getValue().jti);
        assertEquals(claims.getExpiration().toInstant(), captor.getValue().expiresAt);
    }
}
