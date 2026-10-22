package dev.keiba;
import java.util.Map;
import org.springframework.web.bind.annotation.*;
@RestController
class HealthController {
 @GetMapping("/api/health") Map<String,String> health() { return Map.of("status","ok"); }
}
