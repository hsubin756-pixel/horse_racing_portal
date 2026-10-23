package dev.keiba;
import java.time.*;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

@Service @Transactional(readOnly=true)
class RacingInsights {
 final JdbcTemplate db;final CatalogService catalog;final Clock clock;
 RacingInsights(JdbcTemplate db,CatalogService catalog,Clock clock){this.db=db;this.catalog=catalog;this.clock=clock;}
 record Point(int distance,Integer position,Double cumulativeSeconds,Double segmentSeconds,String source){}
 record Run(long raceId,String raceName,LocalDate raceDate,int distance,long horseId,String horseName,int number,int fieldSize,Integer finishPosition,String style,Double last600,List<Point> points){}
 record Style(long horseId,String style,int samples,int completedStarts,Map<String,Long> distribution,List<Run> runs,String explanation){}
 static String classify(Integer position,int fieldSize){
  if(position==null||fieldSize<2||position<1||position>fieldSize)return "판단 보류";
  if(position==1)return "선행";
  if(position<=Math.ceil(fieldSize/3.0))return "선입";
  if(position<=Math.ceil(fieldSize*2/3.0))return "중단";
  return "추입";
 }
 List<Run> runs(String where,Object...args){
  var rows=db.queryForList("SELECT e.id,e.horse_id,h.name horse_name,e.number,e.finish_position,r.id race_id,r.name race_name,r.race_date,r.distance,r.status race_status,e.status entry_status,(SELECT COUNT(*) FROM entry f WHERE f.race_id=r.id AND f.status<>'SCRATCHED') field_size FROM entry e JOIN horse h ON h.id=e.horse_id JOIN race r ON r.id=e.race_id WHERE "+where+" ORDER BY r.race_date DESC,r.id DESC,e.number LIMIT 200",args);
  if(rows.isEmpty())return List.of();
  var ids=rows.stream().map(r->r.get("id")).toList();
  var all=db.queryForList("SELECT * FROM sectional WHERE entry_id IN ("+String.join(",",Collections.nCopies(ids.size(),"?"))+") ORDER BY distance",ids.toArray());
  return rows.stream().map(row->{
   var points=new ArrayList<Point>();Double previous=0.0;
   for(var p:all){if(((Number)p.get("entry_id")).longValue()!=((Number)row.get("id")).longValue())continue;
    Double seconds=num(p.get("cumulative_seconds"));
    points.add(new Point(((Number)p.get("distance")).intValue(),integer(p.get("position")),seconds,seconds==null||previous==null?null:Math.round((seconds-previous)*100.0)/100.0,(String)p.get("source")));
    previous=seconds;
   }
   int distance=((Number)row.get("distance")).intValue(),field=((Number)row.get("field_size")).intValue();
   Integer early=points.stream().filter(p->p.distance()<=Math.min(600,distance/2)&&p.position()!=null).map(Point::position).findFirst().orElse(null);
   Double at600=points.stream().filter(p->p.distance()==distance-600).map(Point::cumulativeSeconds).filter(Objects::nonNull).findFirst().orElse(null);
   Double atFinish=points.stream().filter(p->p.distance()==distance).map(Point::cumulativeSeconds).filter(Objects::nonNull).findFirst().orElse(null);
   boolean official="OFFICIAL".equals(row.get("race_status"))&&"FINISHED".equals(row.get("entry_status"))&&!((java.sql.Date)row.get("race_date")).toLocalDate().isAfter(LocalDate.now(clock));
   return new Run(((Number)row.get("race_id")).longValue(),(String)row.get("race_name"),((java.sql.Date)row.get("race_date")).toLocalDate(),distance,((Number)row.get("horse_id")).longValue(),(String)row.get("horse_name"),((Number)row.get("number")).intValue(),field,integer(row.get("finish_position")),official?classify(early,field):"판단 보류",at600==null||atFinish==null?null:Math.round((atFinish-at600)*100.0)/100.0,List.copyOf(points));
  }).toList();
 }
 static Integer integer(Object n){return n==null?null:((Number)n).intValue();}
 static Double num(Object n){return n==null?null:((Number)n).doubleValue();}
 List<Run> race(long id){catalog.requireRace(id);return runs("r.id=?",id);}
 Style horse(long id){
  catalog.requireHorse(id);
  var recent=runs("e.horse_id=? AND r.status='OFFICIAL' AND e.status='FINISHED' AND r.race_date<=?",id,LocalDate.now(clock)).stream().limit(10).toList();
  var distribution=new LinkedHashMap<String,Long>();for(String s:List.of("선행","선입","중단","추입"))distribution.put(s,recent.stream().filter(r->r.style().equals(s)).count());
  int samples=distribution.values().stream().mapToInt(Long::intValue).sum();
  var top=distribution.entrySet().stream().max(Map.Entry.comparingByValue()).orElseThrow();
  String style=samples<3?"판단 보류":top.getValue()/(double)samples>=.6?top.getKey():"혼합형";
  return new Style(id,style,samples,recent.size(),distribution,recent,"최근 완료 10경주 중 초반(600m 이내·전체 거리 절반 이내) 통과 순위가 있는 기록을 집계합니다. 1위=선행, 상위 1/3=선입, 중간 1/3=중단, 후미 1/3=추입. 유효 기록 3개 이상이고 60% 이상 같은 유형일 때 대표 스타일로 표시합니다. 추입은 후미 출발 경향이며 막판 가속이나 역전을 보장하지 않습니다. 공식 각질 판정이나 예측 결과가 아닙니다.");
 }
 List<Map<String,Object>> calendar(String month,String venue){
  YearMonth ym;try{ym=YearMonth.parse(month);}catch(Exception e){throw new ApiException(400,"조회 월은 YYYY-MM 형식으로 입력하세요.");}
  if(ym.getYear()<1900||ym.getYear()>2200||venue.length()>100)throw new ApiException(400,"월·경마장을 확인하세요.");
  return db.queryForList("SELECT id,name,race_date,start_time,venue,distance,surface,status FROM race WHERE race_date BETWEEN ? AND ? AND (?='' OR venue=?) ORDER BY race_date,start_time,id",ym.atDay(1),ym.atEndOfMonth(),venue,venue);
 }
 List<Map<String,Object>> payouts(long id){catalog.requireRace(id);return db.queryForList("SELECT id,market,combination,status,odds,amount_yen,source,as_of FROM payout WHERE race_id=? ORDER BY market,combination",id);}
}
@RestController @RequestMapping("/api")
class RacingInsightsController {
 final RacingInsights service;RacingInsightsController(RacingInsights service){this.service=service;}
 @GetMapping("/races/{id}/sectionals") Object race(@PathVariable long id){return service.race(id);}
 @GetMapping("/horses/{id}/running-style") Object horse(@PathVariable long id){return service.horse(id);}
 @GetMapping("/races/{id}/payouts") Object payouts(@PathVariable long id){return service.payouts(id);}
 @GetMapping("/races/calendar") Object calendar(@RequestParam String month,@RequestParam(defaultValue="") String venue){return service.calendar(month,venue);}
}
