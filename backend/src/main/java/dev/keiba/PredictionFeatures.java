package dev.keiba;
import java.util.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
/** Finish database work before waiting for the remote model service. */
@Service
class PredictionFeatures {
 final CatalogService catalog; final EntryRepository entries;
 PredictionFeatures(CatalogService catalog,EntryRepository entries) { this.catalog=catalog;this.entries=entries; }
 record Input(Map<Long,String> names,List<PredictService.Features> horses) {}
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
  return new Input(Map.copyOf(names),features);
 }
}
