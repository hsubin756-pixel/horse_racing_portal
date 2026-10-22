package dev.keiba;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.List;
import org.springframework.stereotype.Component;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.web.filter.OncePerRequestFilter;
@Component
class JwtFilter extends OncePerRequestFilter {
 final JwtService jwt; final RevokedTokenRepository revoked; final MemberRepository members;
 JwtFilter(JwtService j,RevokedTokenRepository r,MemberRepository m) {jwt=j;revoked=r;members=m;}
 @Override protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain) throws ServletException,IOException {
  String h=req.getHeader("Authorization");
  if(h!=null) {
   try {
    if(!h.startsWith("Bearer ")) throw new IllegalArgumentException();
    var c=jwt.parse(h.substring(7)); Long id=Long.valueOf(c.getSubject());
    if(c.getId()==null || revoked.existsById(c.getId()) || !members.existsById(id)) throw new IllegalArgumentException();
    SecurityContextHolder.getContext().setAuthentication(new UsernamePasswordAuthenticationToken(id,null,List.of()));
   } catch(io.jsonwebtoken.JwtException | IllegalArgumentException e) {
    SecurityContextHolder.clearContext();res.setStatus(401);res.setContentType("application/json;charset=UTF-8");res.getWriter().write("{\"message\":\"인증이 만료되었거나 유효하지 않습니다. 다시 로그인하세요.\"}");return;
   }
  }
  chain.doFilter(req,res);
 }
}
