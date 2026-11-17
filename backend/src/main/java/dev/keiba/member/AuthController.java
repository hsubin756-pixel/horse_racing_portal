package dev.keiba.member;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
class AuthController {

    private final AuthService service;

    AuthController(AuthService service) {
        this.service = service;
    }

    record Register(
        @NotBlank @Email @Size(max = 254) String email,
        @NotBlank @Size(min = 10, max = 72) String password,
        @NotBlank @Size(max = 40) String nickname
    ) {}

    record Login(@NotBlank @Email @Size(max = 254) String email, @NotBlank @Size(max = 72) String password) {}

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    void register(@Valid @RequestBody Register request) {
        service.register(request);
    }

    @PostMapping("/login")
    Object login(@Valid @RequestBody Login request) {
        return service.login(request);
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void logout(@RequestHeader("Authorization") String authorization) {
        service.logout(authorization);
    }
}
