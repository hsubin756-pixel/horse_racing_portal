package dev.keiba;
import org.springframework.web.bind.annotation.*;
@RestController
class PredictController {
 final PredictService service;
 PredictController(PredictService service) {this.service=service;}
 @PostMapping("/api/races/{id}/prediction") Object predict(@PathVariable Long id) {return service.predict(id);}
}
