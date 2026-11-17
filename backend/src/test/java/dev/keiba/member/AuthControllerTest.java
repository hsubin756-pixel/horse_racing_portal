package dev.keiba.member;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import dev.keiba.common.ApiException;
import dev.keiba.security.JwtService;
import dev.keiba.security.SecurityConfig;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/** 요청 본문 검증(Bean Validation)과 예외 → HTTP 상태 변환(ApiExceptionHandler)을 웹 계층에서 확인합니다. */
@WebMvcTest(
    controllers = AuthController.class,
    properties = { "app.jwt-secret=" + AuthControllerTest.SECRET, "app.jwt-ttl-seconds=1800" }
)
@Import({ SecurityConfig.class, JwtService.class })
class AuthControllerTest {

    static final String SECRET = "test-only-key-never-use-in-production-12345678901234567890";

    @Autowired
    MockMvc mvc;

    @Autowired
    JwtService jwt;

    @MockitoBean
    AuthService service;

    @MockitoBean
    MemberRepository members;

    @MockitoBean
    RevokedTokenRepository revoked;

    static String json(String email, String password, String nickname) {
        return "{\"email\":\"" + email + "\",\"password\":\"" + password + "\",\"nickname\":\"" + nickname + "\"}";
    }

    @Test
    void registerIsPublicAndReturns201() throws Exception {
        mvc.perform(
            post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json("new@example.com", "correct-horse-1", "기수"))
        ).andExpect(status().isCreated());
        verify(service).register(new AuthController.Register("new@example.com", "correct-horse-1", "기수"));
    }

    @Test
    void registerValidatesInputBeforeTheService() throws Exception {
        for (String body : new String[] {
            json("not-an-email", "correct-horse-1", "기수"),
            json("new@example.com", "short", "기수"),
            json("new@example.com", "correct-horse-1", ""),
            "{\"email\":\"new@example.com\"}",
            "not json"
        }) {
            mvc.perform(post("/api/auth/register").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").isNotEmpty());
        }
        verifyNoInteractions(service);
    }

    @Test
    void duplicateEmailBecomes409() throws Exception {
        doThrow(new ApiException(409, "이미 가입된 이메일입니다.")).when(service).register(any());
        mvc.perform(
            post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json("dup@example.com", "correct-horse-1", "기수"))
        )
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.message").isNotEmpty());
    }

    @Test
    void wrongCredentialsBecome401() throws Exception {
        when(service.login(any())).thenThrow(new ApiException(401, "이메일 또는 비밀번호가 올바르지 않습니다."));
        mvc.perform(
            post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\":\"a@example.com\",\"password\":\"wrong-pass\"}")
        ).andExpect(status().isUnauthorized());
    }

    @Test
    void loginResponseCarriesTokenFields() throws Exception {
        when(service.login(any())).thenReturn(new AuthService.LoginResult("signed.jwt.value", "기수", 1800));
        mvc.perform(
            post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\":\"a@example.com\",\"password\":\"correct-horse-1\"}")
        )
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.token").value("signed.jwt.value"))
            .andExpect(jsonPath("$.expiresIn").value(1800));
    }

    @Test
    void logoutRequiresAValidToken() throws Exception {
        mvc.perform(post("/api/auth/logout")).andExpect(status().isUnauthorized());
        verifyNoInteractions(service);
        when(members.existsById(3L)).thenReturn(true);
        String header = "Bearer " + jwt.create(3L);
        mvc.perform(post("/api/auth/logout").header("Authorization", header)).andExpect(status().isNoContent());
        verify(service).logout(header);
    }
}
