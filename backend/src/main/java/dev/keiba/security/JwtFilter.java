package dev.keiba.security;

import dev.keiba.member.MemberRepository;
import dev.keiba.member.RevokedTokenRepository;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.List;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
class JwtFilter extends OncePerRequestFilter {

    private final JwtService jwt;
    private final RevokedTokenRepository revoked;
    private final MemberRepository members;

    JwtFilter(JwtService jwt, RevokedTokenRepository revoked, MemberRepository members) {
        this.jwt = jwt;
        this.revoked = revoked;
        this.members = members;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
        throws ServletException, IOException
    {
        String header = req.getHeader("Authorization");
        // 헤더가 없으면 익명으로 통과시키고, 접근 허용 여부는 SecurityConfig의 규칙이 결정합니다.
        if (header != null) {
            try {
                if (!header.startsWith("Bearer ")) {
                    throw new IllegalArgumentException();
                }
                var claims = jwt.parse(header.substring("Bearer ".length()));
                Long memberId = Long.valueOf(claims.getSubject());
                // 로그아웃으로 철회된 토큰이거나 탈퇴한 회원이면 서명이 맞아도 거부합니다.
                if (claims.getId() == null || revoked.existsById(claims.getId()) || !members.existsById(memberId)) {
                    throw new IllegalArgumentException();
                }
                SecurityContextHolder.getContext().setAuthentication(
                    new UsernamePasswordAuthenticationToken(memberId, null, List.of())
                );
            } catch (io.jsonwebtoken.JwtException | IllegalArgumentException e) {
                SecurityContextHolder.clearContext();
                res.setStatus(401);
                res.setContentType("application/json;charset=UTF-8");
                res.getWriter().write("{\"message\":\"인증이 만료되었거나 유효하지 않습니다. 다시 로그인하세요.\"}");
                return;
            }
        }
        chain.doFilter(req, res);
    }
}
