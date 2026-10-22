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
 record HorseView(Long id,String name,String sex,LocalDate birthDate,String color,String trainer,HorseRef sire,HorseRef dam) {}
 record RaceView(Long id,String name,LocalDate raceDate,String venue,int distance,String surface) {}
 record EntryView(Long horseId,String horseName,Long raceId,String raceName,LocalDate raceDate,int number,String jockey,Integer finishPosition,java.math.BigDecimal timeSeconds) {}
 record PageView<T>(List<T> content,int page,int totalPages,long totalElements) {}
 record RaceDetail(RaceView race,List<EntryView> entries) {}
 Horse requireHorse(Long id) { return horses.findById(id).orElseThrow(()->new ApiException(404,"경주마를 찾을 수 없습니다.")); }
 Race requireRace(Long id) { return races.findById(id).orElseThrow(()->new ApiException(404,"경주를 찾을 수 없습니다.")); }
 HorseRef ref(Horse h) { if(h==null) return null; h=org.hibernate.Hibernate.unproxy(h,Horse.class); return new HorseRef(h.id,h.name); }
 HorseView view(Horse h) { h=org.hibernate.Hibernate.unproxy(h,Horse.class); return new HorseView(h.id,h.name,h.sex,h.birthDate,h.color,h.trainer,ref(h.sire),ref(h.dam)); }
 RaceView view(Race r) { r=org.hibernate.Hibernate.unproxy(r,Race.class); return new RaceView(r.id,r.name,r.raceDate,r.venue,r.distance,r.surface); }
 EntryView view(Entry e) { Horse h=org.hibernate.Hibernate.unproxy(e.horse,Horse.class); Race r=org.hibernate.Hibernate.unproxy(e.race,Race.class); return new EntryView(h.id,h.name,r.id,r.name,r.raceDate,e.number,e.jockey,e.finishPosition,e.timeSeconds); }
 PageView<HorseView> horses(String q,int page,String sort,String direction) {
  if(page<0 || page>100000 || !Set.of("name","sex","birthDate").contains(sort) || !Set.of("asc","desc").contains(direction) || q.length()>100) throw new ApiException(400,"검색 조건을 확인하세요.");
  Page<Horse> p=horses.findByNameContainingIgnoreCase(q,PageRequest.of(page,20,Sort.by(Sort.Direction.fromString(direction),sort).and(Sort.by("id"))));
  return new PageView<>(p.getContent().stream().map(this::view).toList(),p.getNumber(),p.getTotalPages(),p.getTotalElements());
 }
 HorseView horse(Long id) { return view(requireHorse(id)); }
 List<EntryView> history(Long id) { requireHorse(id); return entries.findByHorseIdOrderByRaceRaceDateDesc(id).stream().map(this::view).toList(); }
 PageView<RaceView> races(String q,LocalDate date,int page) {
  if(page<0 || page>100000 || q.length()>150) throw new ApiException(400,"검색 조건을 확인하세요.");
  var p=races.search(q,date,PageRequest.of(page,20,Sort.by(Sort.Direction.DESC,"raceDate").and(Sort.by("id"))));
  return new PageView<>(p.getContent().stream().map(this::view).toList(),p.getNumber(),p.getTotalPages(),p.getTotalElements());
 }
 RaceDetail race(Long id) { return new RaceDetail(view(requireRace(id)),entries.findByRaceIdOrderByNumberAsc(id).stream().map(this::view).toList()); }

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
