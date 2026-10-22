package dev.keiba;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.HttpStatus;
@RestController @RequestMapping("/api/auth")
class AuthController {
 final AuthService service;
 AuthController(AuthService s) {service=s;}
 record Register(@NotBlank @Email @Size(max=254) String email,@NotBlank @Size(min=10,max=72) String password,@NotBlank @Size(max=40) String nickname) {}
 record Login(@NotBlank @Email @Size(max=254) String email,@NotBlank @Size(max=72) String password) {}
 @PostMapping("/register") @ResponseStatus(HttpStatus.CREATED) void register(@Valid @RequestBody Register r) {service.register(r);}
 @PostMapping("/login") Object login(@Valid @RequestBody Login r) {return service.login(r);}
 @PostMapping("/logout") @ResponseStatus(HttpStatus.NO_CONTENT) void logout(@RequestHeader("Authorization") String authorization) {service.logout(authorization);}
}
