package dev.keiba;
import java.time.LocalDate;
import java.util.List;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api")
class AnalyticsController {
 private final AnalyticsService analytics;
 AnalyticsController(AnalyticsService analytics){this.analytics=analytics;}
 @GetMapping("/horses/compare") Object compare(@RequestParam List<Long> ids,@RequestParam(required=false) Integer distance,
  @RequestParam(required=false) String surface,@RequestParam(required=false) LocalDate from,@RequestParam(required=false) LocalDate to) {
  return analytics.compare(ids,AnalyticsService.filter(distance,surface,from,to));
 }
 @GetMapping("/horses/{id}/stats") Object horse(@PathVariable Long id,@RequestParam(required=false) Integer distance,
  @RequestParam(required=false) String surface,@RequestParam(required=false) LocalDate from,@RequestParam(required=false) LocalDate to) {
  return analytics.compare(List.of(id),AnalyticsService.filter(distance,surface,from,to));
 }
 @GetMapping("/jockeys") Object jockeys(@RequestParam(defaultValue="") String q){return analytics.jockeys(q);}
 @GetMapping("/jockeys/stats") Object jockey(@RequestParam String name,@RequestParam(required=false) Integer distance,
  @RequestParam(required=false) String surface,@RequestParam(required=false) LocalDate from,@RequestParam(required=false) LocalDate to) {
  return analytics.jockey(name,AnalyticsService.filter(distance,surface,from,to));
 }
}
