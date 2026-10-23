package dev.keiba;

import java.time.*;
import java.util.*;
import java.util.function.Function;
import org.hibernate.Hibernate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service @Transactional(readOnly=true)
class AnalyticsService {
 private final CatalogService catalog;
 private final EntryRepository entries;
 private final Clock clock;
 AnalyticsService(CatalogService catalog,EntryRepository entries,Clock clock) {
  this.catalog=catalog;this.entries=entries;this.clock=clock;
 }
 record Filter(Integer distance,String surface,LocalDate from,LocalDate to) {}
 record Totals(int starts,int wins,int top3,Double winRate,Double top3Rate,Double averageFinish,Integer bestFinish) {}
 record Breakdown(String condition,Totals totals) {}
 record Recent(Long raceId,String raceName,LocalDate raceDate,Long horseId,String horseName,String jockey,int distance,String surface,int finishPosition) {}
 record Statistics(Totals totals,List<Breakdown> byDistance,List<Breakdown> bySurface,List<Recent> recent) {}
 record HorseStats(CatalogService.HorseView horse,Statistics statistics) {}
 record Comparison(LocalDate asOfDate,String dataKind,Filter filter,List<HorseStats> horses) {}
 record JockeyStats(LocalDate asOfDate,String dataKind,String jockey,Filter filter,Statistics statistics) {}

 static Filter filter(Integer distance,String surface,LocalDate from,LocalDate to) {
  surface=surface==null||surface.isBlank()?null:surface.strip();
  if(distance!=null&&(distance<400||distance>10000) || surface!=null&&!Set.of("잔디","더트","장애").contains(surface)
    || from!=null&&to!=null&&from.isAfter(to)) throw new ApiException(400,"거리·주로·조회 기간을 확인하세요.");
  return new Filter(distance,surface,from,to);
 }
 Comparison compare(List<Long> ids,Filter filter) {
  if(ids==null||ids.isEmpty()||ids.size()>4||ids.stream().anyMatch(id->id==null||id<=0)||new HashSet<>(ids).size()!=ids.size())
   throw new ApiException(400,"서로 다른 경주마를 1~4두 선택하세요.");
  var today=LocalDate.now(clock);
  var horses=ids.stream().map(catalog::horse).toList();
  var completed=entries.findForComparison(new HashSet<>(ids),today);
  var result=horses.stream().map(h->new HorseStats(h,summarize(completed.stream()
   .filter(e->Hibernate.unproxy(e.horse,Horse.class).id.equals(h.id())).toList(),filter,today))).toList();
  return new Comparison(today,completed.stream().allMatch(e->"synthetic_fixture".equals(Hibernate.unproxy(e.race,Race.class).source))?"synthetic_fixture":"admin_catalog",filter,result);
 }
 List<String> jockeys(String q) {
  if(q.length()>100) throw new ApiException(400,"기수 이름은 100자 이하로 입력하세요.");
  return entries.jockeyNames().stream().filter(name->name.toLowerCase(Locale.ROOT).contains(q.strip().toLowerCase(Locale.ROOT))).limit(50).toList();
 }
 JockeyStats jockey(String name,Filter filter) {
  if(name==null||name.isBlank()||name.length()>100) throw new ApiException(400,"기수 이름을 확인하세요.");
  var starts=entries.findByJockeyOrderByRaceRaceDateDescRaceIdDesc(name.strip());
  if(starts.isEmpty()) throw new ApiException(404,"기수를 찾을 수 없습니다.");
  var today=LocalDate.now(clock);
  return new JockeyStats(today,starts.stream().allMatch(e->"synthetic_fixture".equals(Hibernate.unproxy(e.race,Race.class).source))?"synthetic_fixture":"admin_catalog",name.strip(),filter,summarize(starts,filter,today));
 }
 static Statistics summarize(List<Entry> starts,Filter filter,LocalDate today) {
  var completed=starts.stream().filter(e->{
   Race race=Hibernate.unproxy(e.race,Race.class);
   return "OFFICIAL".equals(race.status)&&"FINISHED".equals(e.status)&&e.finishPosition!=null&&!race.raceDate.isAfter(today)
    &&(filter.distance()==null||race.distance==filter.distance())
    &&(filter.surface()==null||race.surface.equals(filter.surface()))
    &&(filter.from()==null||!race.raceDate.isBefore(filter.from()))
    &&(filter.to()==null||!race.raceDate.isAfter(filter.to()));
  }).sorted(Comparator.comparing((Entry e)->Hibernate.unproxy(e.race,Race.class).raceDate).reversed()
    .thenComparing(e->Hibernate.unproxy(e.race,Race.class).id,Comparator.reverseOrder()).thenComparingInt(e->e.number)).toList();
  var recent=completed.stream().limit(5).map(e->{
   Race r=Hibernate.unproxy(e.race,Race.class);Horse h=Hibernate.unproxy(e.horse,Horse.class);
   return new Recent(r.id,r.name,r.raceDate,h.id,h.name,e.jockey,r.distance,r.surface,e.finishPosition);
  }).toList();
  return new Statistics(totals(completed),groups(completed,e->String.valueOf(Hibernate.unproxy(e.race,Race.class).distance),Comparator.comparingInt(Integer::parseInt)),
   groups(completed,e->Hibernate.unproxy(e.race,Race.class).surface,Comparator.naturalOrder()),recent);
 }
 private static List<Breakdown> groups(List<Entry> starts,Function<Entry,String> key,Comparator<String> comparator) {
  var groups=new TreeMap<String,List<Entry>>(comparator);
  for(var e:starts) groups.computeIfAbsent(key.apply(e),ignored->new ArrayList<>()).add(e);
  return groups.entrySet().stream().map(e->new Breakdown(e.getKey(),totals(e.getValue()))).toList();
 }
 static Totals totals(List<Entry> starts) {
  int count=starts.size(),wins=(int)starts.stream().filter(e->e.finishPosition==1).count(),top3=(int)starts.stream().filter(e->e.finishPosition<=3).count();
  return new Totals(count,wins,top3,count==0?null:100.0*wins/count,count==0?null:100.0*top3/count,
   count==0?null:starts.stream().mapToInt(e->e.finishPosition).average().orElseThrow(),
   count==0?null:starts.stream().mapToInt(e->e.finishPosition).min().orElseThrow());
 }
}
