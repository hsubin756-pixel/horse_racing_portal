package dev.keiba;
import org.springframework.context.annotation.*;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
@Configuration
class SecurityConfig {
 @Bean SecurityFilterChain chain(HttpSecurity http) throws Exception {
  return http.csrf(c -> c.disable()).authorizeHttpRequests(a -> a.anyRequest().permitAll()).build();
 }
}
