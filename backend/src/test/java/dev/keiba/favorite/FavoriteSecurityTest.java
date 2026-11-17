package dev.keiba.favorite;

import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.keiba.member.MemberRepository;
import dev.keiba.member.RevokedTokenRepository;
import dev.keiba.security.JwtService;
import dev.keiba.security.SecurityConfig;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * 웹 계층 슬라이스 테스트(@WebMvcTest): 실제 SecurityConfig·JwtFilter·JwtService를 올리고
 * DB 대신 리포지토리를 대역으로 둡니다. 화면에서 버튼을 숨기는 것과 별개로 서버가 인증을 강제하는지 확인합니다.
 */
@WebMvcTest(
    controllers = FavoriteController.class,
    properties = { "app.jwt-secret=" + FavoriteSecurityTest.SECRET, "app.jwt-ttl-seconds=1800" }
)
@Import({ SecurityConfig.class, JwtService.class })
class FavoriteSecurityTest {

    static final String SECRET = "test-only-key-never-use-in-production-12345678901234567890";

    @Autowired
    MockMvc mvc;

    @Autowired
    JwtService jwt;

    @MockitoBean
    FavoriteService favorites;

    @MockitoBean
    MemberRepository members;

    @MockitoBean
    RevokedTokenRepository revoked;

    @BeforeEach
    void membersExist() {
        when(members.existsById(anyLong())).thenReturn(true);
    }

    String bearer(long member) {
        return "Bearer " + jwt.create(member);
    }

    @Test
    void favoritesRequireLogin() throws Exception {
        mvc.perform(get("/api/favorites"))
            .andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.message").isNotEmpty());
        mvc.perform(post("/api/favorites/5")).andExpect(status().isUnauthorized());
        mvc.perform(delete("/api/favorites/5")).andExpect(status().isUnauthorized());
        verifyNoInteractions(favorites);
    }

    @Test
    void validTokenActsOnlyAsTheTokenOwner() throws Exception {
        // 회원 ID는 요청 파라미터가 아니라 서명된 토큰의 sub에서만 결정됩니다.
        mvc.perform(get("/api/favorites").header("Authorization", bearer(7))).andExpect(status().isOk());
        mvc.perform(post("/api/favorites/5").header("Authorization", bearer(7))).andExpect(status().isCreated());
        mvc.perform(delete("/api/favorites/5").header("Authorization", bearer(8))).andExpect(status().isNoContent());
        verify(favorites).list(7L);
        verify(favorites).add(7L, 5L);
        verify(favorites).remove(8L, 5L);
    }

    @Test
    void malformedOrForeignTokensAreRejected() throws Exception {
        String otherKey = Jwts.builder()
            .issuer("keiba-field")
            .subject("7")
            .id(UUID.randomUUID().toString())
            .issuedAt(new Date())
            .expiration(Date.from(Instant.now().plusSeconds(600)))
            .signWith(
                Keys.hmacShaKeyFor("another-key-that-is-long-enough-for-hmac-sha".getBytes(StandardCharsets.UTF_8))
            )
            .compact();
        for (String header : new String[] {
            "Bearer not-a-jwt",
            "Basic dXNlcjpwYXNz",
            jwt.create(7L),
            "Bearer " + otherKey
        }) {
            mvc.perform(get("/api/favorites").header("Authorization", header)).andExpect(status().isUnauthorized());
        }
        verifyNoInteractions(favorites);
    }

    @Test
    void expiredTokenIsRejected() throws Exception {
        var now = Instant.now();
        String expired = Jwts.builder()
            .issuer("keiba-field")
            .subject("7")
            .id(UUID.randomUUID().toString())
            .issuedAt(Date.from(now.minusSeconds(120)))
            .expiration(Date.from(now.minusSeconds(60)))
            .signWith(Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8)))
            .compact();
        mvc.perform(get("/api/favorites").header("Authorization", "Bearer " + expired)).andExpect(
            status().isUnauthorized()
        );
        verifyNoInteractions(favorites);
    }

    @Test
    void loggedOutTokenIsRejected() throws Exception {
        String token = jwt.create(7L);
        when(revoked.existsById(jwt.parse(token).getId())).thenReturn(true);
        mvc.perform(get("/api/favorites").header("Authorization", "Bearer " + token)).andExpect(
            status().isUnauthorized()
        );
        verifyNoInteractions(favorites);
    }

    @Test
    void tokenOfDeletedMemberIsRejected() throws Exception {
        when(members.existsById(7L)).thenReturn(false);
        mvc.perform(get("/api/favorites").header("Authorization", bearer(7))).andExpect(status().isUnauthorized());
        verifyNoInteractions(favorites);
    }

    @Test
    void predictionRequiresLoginAndUnknownPathsAreDenied() throws Exception {
        mvc.perform(post("/api/races/1/prediction")).andExpect(status().isUnauthorized());
        // anyRequest().denyAll(): 허용 목록에 없는 경로는 로그인해도 403
        mvc.perform(get("/api/internal/anything").header("Authorization", bearer(7))).andExpect(status().isForbidden());
    }
}
