package dev.keiba;
import java.time.*;
import java.util.*;
import org.hibernate.Hibernate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service @Transactional
class WatchlistService {
 private final RaceFavoriteRepository favorites;
 private final MemberRepository members;
 private final CatalogService catalog;
 private final EntryRepository entries;
 private final RaceRepository races;
 private final Clock clock;
 WatchlistService(RaceFavoriteRepository favorites,MemberRepository members,CatalogService catalog,EntryRepository entries,RaceRepository races,Clock clock){
  this.favorites=favorites;this.members=members;this.catalog=catalog;this.entries=entries;this.races=races;this.clock=clock;
 }
 @Transactional(readOnly=true) List<CatalogService.RaceView> list(Long user){
  return favorites.findByMemberIdOrderByRaceRaceDateAscRaceIdAsc(user).stream().map(f->catalog.view(f.race)).toList();
 }
 void add(Long user,Long race){
  if(favorites.existsByMemberIdAndRaceId(user,race))throw new ApiException(409,"이미 관심 경주에 등록되어 있습니다.");
  favorites.saveAndFlush(new RaceFavorite(members.findById(user).orElseThrow(()->new ApiException(401,"다시 로그인하세요.")),catalog.requireRace(race)));
 }
 void remove(Long user,Long race){favorites.deleteByMemberIdAndRaceId(user,race);}
 record ScheduledRace(CatalogService.RaceView race,boolean savedRace,List<CatalogService.HorseRef> favoriteHorses){}
 record Schedule(LocalDate asOfDate,LocalDate through,List<ScheduledRace> races){}
 @Transactional(readOnly=true) Schedule schedule(Long user){
  LocalDate today=LocalDate.now(clock),through=today.plusDays(90);
  var views=new HashMap<Long,CatalogService.RaceView>();var saved=new HashSet<Long>();
  var horses=new HashMap<Long,List<CatalogService.HorseRef>>();
  for(Race race:races.upcomingSaved(user,today,through)){
   var view=catalog.view(race);views.put(view.id(),view);saved.add(view.id());
  }
  for(Entry e:entries.upcomingFavoriteHorses(user,today,through)){
   var view=catalog.view(e.race);views.put(view.id(),view);
   Horse horse=Hibernate.unproxy(e.horse,Horse.class);
   horses.computeIfAbsent(view.id(),ignored->new ArrayList<>()).add(new CatalogService.HorseRef(horse.id,horse.name));
  }
  var result=views.values().stream().sorted(Comparator.comparing(CatalogService.RaceView::raceDate).thenComparing(CatalogService.RaceView::id))
   .map(r->new ScheduledRace(r,saved.contains(r.id()),List.copyOf(horses.getOrDefault(r.id(),List.of())))).toList();
  return new Schedule(today,through,result);
 }
}
