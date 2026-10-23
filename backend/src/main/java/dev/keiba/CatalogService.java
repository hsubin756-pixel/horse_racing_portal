package dev.keiba;
import java.util.*;
import java.time.LocalDate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.data.domain.*;
@Service @Transactional(readOnly=true)
class CatalogService {
 final HorseRepository horses; final RaceRepository races; final EntryRepository entries;
 CatalogService(HorseRepository h,RaceRepository r,EntryRepository e) { horses=h; races=r; entries=e; }
 record HorseRef(Long id,String name) {}
 record HorseView(Long id,String name,String sex,LocalDate birthDate,String color,String trainer,HorseRef sire,HorseRef dam,Long trainerId,String kraId,String source,String nameEn,String origin,String breed,String kraRank,String ownerName,boolean ancestorOnly,com.fasterxml.jackson.databind.JsonNode profile,java.time.Instant profileAsOf) {}
 record RaceView(Long id,String name,LocalDate raceDate,String venue,int distance,String surface,java.time.LocalTime startTime,String raceClass,String weather,String going,String status,String source) {}
 record EntryView(Long horseId,String horseName,Long raceId,String raceName,LocalDate raceDate,int number,String jockey,Integer finishPosition,java.math.BigDecimal timeSeconds,Integer popularityRank,java.math.BigDecimal winOdds,String oddsSource,java.time.Instant oddsAsOf,Integer gate,java.math.BigDecimal carriedWeight,Integer bodyWeight,Integer weightChange,String status,Long jockeyId,Long trainerId,String trainerName,Integer oddsRank,Boolean oddsRankShared,Integer oddsRankField,Integer oddsRankTotal) {
  EntryView withOddsRank(OddsRank r){return r==null?this:new EntryView(horseId,horseName,raceId,raceName,raceDate,number,jockey,finishPosition,timeSeconds,popularityRank,winOdds,oddsSource,oddsAsOf,gate,carriedWeight,bodyWeight,weightChange,status,jockeyId,trainerId,trainerName,r.rank(),r.shared(),r.field(),r.total());}
 }
 /** 배당 기준 인기: 저장된 단승 배당이 낮은 순서의 순위. 공식 인기 순위(popularityRank)와 별개이며 조회 시 계산합니다. */
 record OddsRank(Integer rank,Boolean shared,Integer field,Integer total) {}
 record PageView<T>(List<T> content,int page,int totalPages,long totalElements) {}
 record RaceDetail(RaceView race,List<EntryView> entries) {}
 Horse requireHorse(Long id) { return horses.findById(id).orElseThrow(()->new ApiException(404,"경주마를 찾을 수 없습니다.")); }
 Race requireRace(Long id) { return races.findById(id).orElseThrow(()->new ApiException(404,"경주를 찾을 수 없습니다.")); }
 HorseRef ref(Horse h) { if(h==null) return null; h=org.hibernate.Hibernate.unproxy(h,Horse.class); return new HorseRef(h.id,h.name); }
 static final com.fasterxml.jackson.databind.ObjectMapper JSON=new com.fasterxml.jackson.databind.ObjectMapper();
 /** DB의 JSON 열은 문자열로 읽히므로 응답에서는 객체로 풀어 줍니다. 잘못된 JSON은 null로 처리해 화면이 중단되지 않게 합니다. */
 static com.fasterxml.jackson.databind.JsonNode json(String raw) { try { return raw==null?null:JSON.readTree(raw); } catch(java.io.IOException e) { return null; } }
 HorseView view(Horse h) { h=org.hibernate.Hibernate.unproxy(h,Horse.class); return new HorseView(h.id,h.name,h.sex,h.birthDate,h.color,h.trainer,ref(h.sire),ref(h.dam),h.trainerId,h.kraId,h.source,h.nameEn,h.origin,h.breed,h.kraRank,h.ownerName,h.ancestorKey!=null,json(h.profileJson),h.profileAsOf); }
 RaceView view(Race r) { r=org.hibernate.Hibernate.unproxy(r,Race.class); return new RaceView(r.id,r.name,r.raceDate,r.venue,r.distance,r.surface,r.startTime,r.raceClass,r.weather,r.going,r.status,r.source); }
 EntryView view(Entry e) { Horse h=org.hibernate.Hibernate.unproxy(e.horse,Horse.class); Race r=org.hibernate.Hibernate.unproxy(e.race,Race.class); return new EntryView(h.id,h.name,r.id,r.name,r.raceDate,e.number,e.jockey,e.finishPosition,e.timeSeconds,e.popularityRank,e.winOdds,e.oddsSource,e.oddsAsOf,e.gate,e.carriedWeight,e.bodyWeight,e.weightChange,e.status,e.jockeyId,e.trainerId,e.trainerName,null,null,null,null); }
 PageView<HorseView> horses(String q,int page,String sort,String direction) {
  if(page<0 || page>100000 || !Set.of("name","sex","birthDate").contains(sort) || !Set.of("asc","desc").contains(direction) || q.length()>100) throw new ApiException(400,"검색 조건을 확인하세요.");
  Page<Horse> p=horses.findByNameContainingIgnoreCase(q,PageRequest.of(page,20,Sort.by(Sort.Direction.fromString(direction),sort).and(Sort.by("id"))));
  return new PageView<>(p.getContent().stream().map(this::view).toList(),p.getNumber(),p.getTotalPages(),p.getTotalElements());
 }
 HorseView horse(Long id) { return view(requireHorse(id)); }
 List<EntryView> history(Long id) { requireHorse(id); return withOddsRanks(entries.findByHorseIdOrderByRaceRaceDateDesc(id).stream().filter(e->"OFFICIAL".equals(org.hibernate.Hibernate.unproxy(e.race,Race.class).status)&&"FINISHED".equals(e.status)).map(this::view).filter(e->e.finishPosition()!=null && !e.raceDate().isAfter(LocalDate.now(java.time.ZoneId.of("Asia/Tokyo")))).toList()); }
 PageView<RaceView> races(String q,LocalDate date,int page) {
  if(page<0 || page>100000 || q.length()>150) throw new ApiException(400,"검색 조건을 확인하세요.");
  var p=races.search(q,date,PageRequest.of(page,20,Sort.by(Sort.Direction.DESC,"raceDate").and(Sort.by("id"))));
  return new PageView<>(p.getContent().stream().map(this::view).toList(),p.getNumber(),p.getTotalPages(),p.getTotalElements());
 }
 RaceDetail race(Long id) { return new RaceDetail(view(requireRace(id)),withOddsRanks(entries.findByRaceIdOrderByNumberAsc(id).stream().map(this::view).toList())); }

 /** 조회된 출전 목록의 각 경주에 대해 DB의 단승 배당 전체를 읽어 배당 기준 인기를 채웁니다. 취소 출전은 계산에서 제외합니다. */
 List<EntryView> withOddsRanks(List<EntryView> views) {
  Set<Long> ids=new HashSet<>(); for(var v:views) ids.add(v.raceId());
  if(ids.isEmpty()) return views;
  Map<Long,List<java.math.BigDecimal>> odds=new HashMap<>(); Map<Long,Integer> totals=new HashMap<>();
  for(Object[] row:entries.oddsByRace(ids)) {
   Long raceId=(Long)row[0]; totals.merge(raceId,1,Integer::sum);
   if(row[1]!=null) odds.computeIfAbsent(raceId,k->new ArrayList<>()).add((java.math.BigDecimal)row[1]);
  }
  return views.stream().map(v->v.withOddsRank(oddsRank(v.winOdds(),"SCRATCHED".equals(v.status())?null:odds.get(v.raceId()),totals.getOrDefault(v.raceId(),0)))).toList();
 }
 /** 배당이 낮을수록 상위. 같은 배당은 공동 순위(1,2,2,4 방식). own이 null이거나 계산 대상이 아니면 순위를 비웁니다. */
 static OddsRank oddsRank(java.math.BigDecimal own,List<java.math.BigDecimal> field,int total) {
  if(own==null || field==null || field.isEmpty()) return new OddsRank(null,null,field==null?null:field.size(),total);
  int lower=0,same=0; for(var o:field){int c=o.compareTo(own); if(c<0) lower++; else if(c==0) same++;}
  return new OddsRank(lower+1,same>1,field.size(),total);
 }

 record PedigreeNode(Long id,String name,PedigreeNode sire,PedigreeNode dam) {}
 PedigreeNode pedigree(Long id) { return ancestors(requireHorse(id),3,new HashSet<>()); }
 private PedigreeNode ancestors(Horse horse,int depth,Set<Long> path) {
  if(horse==null) return null;
  Horse h=org.hibernate.Hibernate.unproxy(horse,Horse.class);
  if(path.contains(h.id)) return null;
  Set<Long> next=new HashSet<>(path);next.add(h.id);
  return new PedigreeNode(h.id,h.name,depth==0?null:ancestors(h.sire,depth-1,next),depth==0?null:ancestors(h.dam,depth-1,next));
 }
}
