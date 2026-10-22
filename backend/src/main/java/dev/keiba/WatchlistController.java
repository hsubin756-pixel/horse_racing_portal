package dev.keiba;
import org.springframework.web.bind.annotation.*;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.http.HttpStatus;
@RestController @RequestMapping("/api")
class WatchlistController {
 private final WatchlistService watchlist;
 WatchlistController(WatchlistService watchlist){this.watchlist=watchlist;}
 @GetMapping("/race-favorites") Object list(@AuthenticationPrincipal Long user){return watchlist.list(user);}
 @PostMapping("/race-favorites/{id}") @ResponseStatus(HttpStatus.CREATED) void add(@AuthenticationPrincipal Long user,@PathVariable Long id){watchlist.add(user,id);}
 @DeleteMapping("/race-favorites/{id}") @ResponseStatus(HttpStatus.NO_CONTENT) void remove(@AuthenticationPrincipal Long user,@PathVariable Long id){watchlist.remove(user,id);}
 @GetMapping("/my-schedule") Object schedule(@AuthenticationPrincipal Long user){return watchlist.schedule(user);}
}
