package dev.keiba;
import org.springframework.context.annotation.*;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.http.HttpMethod;
@Configuration
class SecurityConfig {
 @Bean org.springframework.boot.web.servlet.FilterRegistrationBean<JwtFilter> jwtRegistration(JwtFilter filter) {
  var registration=new org.springframework.boot.web.servlet.FilterRegistrationBean<>(filter);
  registration.setEnabled(false);return registration;
 }
 @Bean BCryptPasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(12); }
 @Bean SecurityFilterChain chain(HttpSecurity http,JwtFilter jwt) throws Exception {
  return http.csrf(c -> c.disable()).sessionManagement(s->s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
   .authorizeHttpRequests(a->a
    .requestMatchers(HttpMethod.POST,"/api/auth/register","/api/auth/login").permitAll()
    .requestMatchers(HttpMethod.GET,"/api/health","/api/horses","/api/horses/**","/api/races","/api/races/**","/v3/api-docs/**","/swagger-ui/**","/swagger-ui.html").permitAll()
    .requestMatchers("/api/favorites/**","/api/auth/logout","/api/races/*/prediction").authenticated()
    .anyRequest().denyAll())
   .exceptionHandling(e->e.authenticationEntryPoint((req,res,x)->{res.setStatus(401);res.setContentType("application/json;charset=UTF-8");res.getWriter().write("{\"message\":\"로그인이 필요합니다.\"}");})
    .accessDeniedHandler((req,res,x)->{res.setStatus(403);res.setContentType("application/json;charset=UTF-8");res.getWriter().write("{\"message\":\"접근 권한이 없습니다.\"}");}))
   .addFilterBefore(jwt,UsernamePasswordAuthenticationFilter.class).build();
 }
}
