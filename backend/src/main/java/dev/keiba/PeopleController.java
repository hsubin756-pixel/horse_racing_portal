package dev.keiba;
import java.time.*;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

@RestController @RequestMapping("/api/people")
class PeopleController {
 final JdbcTemplate db;final Clock clock;
 PeopleController(JdbcTemplate db,Clock clock){this.db=db;this.clock=clock;}
 @GetMapping Object list(@RequestParam(defaultValue="JOCKEY") String kind,@RequestParam(required=false) Integer year,@RequestParam(defaultValue="") String venue,@RequestParam(defaultValue="") String q){
  validate(kind,year,venue,q);
  return db.queryForList("SELECT p.id,p.kind,p.name,p.source,COUNT(e.id) starts,COALESCE(SUM(e.finish_position=1),0) wins,COALESCE(SUM(e.finish_position<=3),0) top3 FROM person p LEFT JOIN horse h ON p.kind='TRAINER' AND h.trainer_id=p.id LEFT JOIN entry e ON (p.kind='JOCKEY' AND e.jockey_id=p.id OR p.kind='TRAINER' AND e.horse_id=h.id) AND e.status='FINISHED' AND e.finish_position IS NOT NULL AND EXISTS (SELECT r.id FROM race r WHERE r.id=e.race_id AND r.status='OFFICIAL' AND r.race_date<=? AND (? IS NULL OR YEAR(r.race_date)=?) AND (?='' OR r.venue=?)) WHERE p.kind=? AND LOCATE(?,p.name)>0 GROUP BY p.id,p.kind,p.name,p.source ORDER BY wins DESC,starts DESC,p.id LIMIT 100",LocalDate.now(clock),year,year,venue,venue,kind,q);
 }
 @GetMapping("/{id}") Object detail(@PathVariable long id,@RequestParam(required=false) Integer year,@RequestParam(defaultValue="") String venue){
  var rows=db.queryForList("SELECT * FROM person WHERE id=?",id);if(rows.isEmpty())throw new ApiException(404,"인물을 찾을 수 없습니다.");var p=rows.getFirst();validate((String)p.get("kind"),year,venue,"");
  String condition="JOCKEY".equals(p.get("kind"))?"e.jockey_id=?":"h.trainer_id=?";
  String where=" FROM entry e JOIN horse h ON h.id=e.horse_id JOIN race r ON r.id=e.race_id WHERE "+condition+" AND e.status='FINISHED' AND e.finish_position IS NOT NULL AND r.status='OFFICIAL' AND r.race_date<=? AND (? IS NULL OR YEAR(r.race_date)=?) AND (?='' OR r.venue=?)";
  Object[] args={id,LocalDate.now(clock),year,year,venue,venue};
  var totals=db.queryForMap("SELECT COUNT(*) starts,COALESCE(SUM(e.finish_position=1),0) wins,COALESCE(SUM(e.finish_position<=3),0) top3,AVG(e.finish_position) average_finish"+where,args);
  var recent=db.queryForList("SELECT r.id race_id,r.name race_name,r.race_date,h.id horse_id,h.name horse_name,e.finish_position,r.distance,r.surface"+where+" ORDER BY r.race_date DESC,r.id DESC LIMIT 20",args);
  return Map.of("person",p,"totals",totals,"recent",recent,"asOfDate",LocalDate.now(clock));
 }
 void validate(String kind,Integer year,String venue,String q){if(!Set.of("JOCKEY","TRAINER").contains(kind)||year!=null&&(year<1800||year>2200)||venue.length()>100||q.length()>100)throw new ApiException(400,"인물 검색 조건을 확인하세요.");}
}
