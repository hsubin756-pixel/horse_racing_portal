package dev.keiba;
import java.time.LocalDate;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api")
class CatalogController {
 final CatalogService service;
 CatalogController(CatalogService service) { this.service=service; }
 @GetMapping("/horses") Object horses(@RequestParam(defaultValue="") String q,@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="name") String sort,@RequestParam(defaultValue="asc") String direction) { return service.horses(q.trim(),page,sort,direction); }
 @GetMapping("/horses/{id}") Object horse(@PathVariable Long id) { return service.horse(id); }
 @GetMapping("/horses/{id}/history") Object history(@PathVariable Long id) { return service.history(id); }
 @GetMapping("/horses/{id}/pedigree") Object pedigree(@PathVariable Long id) { return service.pedigree(id); }
 @GetMapping("/races") Object races(@RequestParam(defaultValue="") String q,@RequestParam(required=false) LocalDate date,@RequestParam(defaultValue="0") int page) { return service.races(q.trim(),date,page); }
 @GetMapping("/races/{id}") Object race(@PathVariable Long id) { return service.race(id); }
}
