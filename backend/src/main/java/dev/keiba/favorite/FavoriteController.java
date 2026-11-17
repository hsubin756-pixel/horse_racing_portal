package dev.keiba.favorite;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/favorites")
class FavoriteController {

    private final FavoriteService service;

    FavoriteController(FavoriteService service) {
        this.service = service;
    }

    @GetMapping
    Object list(@AuthenticationPrincipal Long user) {
        return service.list(user);
    }

    @PostMapping("/{horse}")
    @ResponseStatus(HttpStatus.CREATED)
    void add(@AuthenticationPrincipal Long user, @PathVariable Long horse) {
        service.add(user, horse);
    }

    @DeleteMapping("/{horse}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void remove(@AuthenticationPrincipal Long user, @PathVariable Long horse) {
        service.remove(user, horse);
    }
}
