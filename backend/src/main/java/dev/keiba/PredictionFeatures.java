package dev.keiba;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
/** Finish database work before waiting for the remote model service. */
@Service
class PredictionFeatures {
 final CatalogService catalog; final EntryRepository entries;
 PredictionFeatures(CatalogService catalog,EntryRepository entries) { this.catalog=catalog;this.entries=entries; }
 /** real=true: 한국마사회 경주. 실제 데이터 실험 모델에 넘길 출주마 식별·신체 정보를 DB에서 모읍니다(전적은 ML 서비스의 보존 이력 사용). */
 record Input(Map<Long,String> names,List<PredictService.Features> horses,boolean real,PredictService.RealRequest realRequest) {}
 @Transactional(readOnly=true) Input forRace(Long raceId) {
  Race race=catalog.requireRace(raceId);
  if("CANCELLED".equals(race.status))throw new ApiException(400,"취소된 경주는 예측할 수 없습니다.");
  var starters=entries.findByRaceIdOrderByNumberAsc(raceId).stream().filter(e->!Set.of("SCRATCHED","DISQUALIFIED","DNF").contains(e.status)).toList();
  if(starters.isEmpty()) throw new ApiException(400,"출주마가 없는 경주는 예측할 수 없습니다.");
  var names=new HashMap<Long,String>();
  for(var entry:starters) {
   var horse=org.hibernate.Hibernate.unproxy(entry.horse,Horse.class);
   names.put(horse.id,horse.name);
  }
  if(race.source!=null&&race.source.startsWith("KRA_")) {
   var horses=new ArrayList<PredictService.RealHorse>();
   for(var entry:starters) {
    var horse=org.hibernate.Hibernate.unproxy(entry.horse,Horse.class);
    if(horse.kraId==null||!horse.kraId.matches("\\d{1,16}")) throw new ApiException(400,"한국마사회 마번이 없는 출주마가 있어 실제 데이터 모델을 적용할 수 없습니다.");
    horses.add(new PredictService.RealHorse(horse.id,horse.kraId,entry.carriedWeight==null?null:entry.carriedWeight.doubleValue(),entry.bodyWeight,entry.gate,horse.birthDate==null?null:horse.birthDate.toString(),horse.sex,entry.jockey,entry.trainerName));
   }
   horses.sort(Comparator.comparing(PredictService.RealHorse::horseId));
   return new Input(Map.copyOf(names),List.of(),true,new PredictService.RealRequest(race.raceDate.toString(),race.distance,horses));
  }
  var past=entries.pastForHorses(names.keySet(),race.raceDate);
  var stats=new HashMap<Long,IntSummaryStatistics>();
  for(var entry:past) {
   var horse=org.hibernate.Hibernate.unproxy(entry.horse,Horse.class);
   stats.computeIfAbsent(horse.id,id->new IntSummaryStatistics()).accept(entry.finishPosition);
  }
  var features=names.keySet().stream().sorted().map(id->{
   var history=stats.get(id);
   return new PredictService.Features(id,history==null?12.5:history.getAverage(),history==null?0:(int)history.getCount(),race.distance);
  }).toList();
  return new Input(Map.copyOf(names),features,false,null);
 }
}
