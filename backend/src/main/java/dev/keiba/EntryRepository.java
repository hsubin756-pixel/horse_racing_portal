package dev.keiba;
import java.util.List;
import java.time.LocalDate;
import org.springframework.data.jpa.repository.*;
interface EntryRepository extends JpaRepository<Entry,Long> {
 @EntityGraph(attributePaths={"horse","race"})
 List<Entry> findByHorseIdOrderByRaceRaceDateDesc(Long id);
 @EntityGraph(attributePaths={"horse","race"})
 List<Entry> findByRaceIdOrderByNumberAsc(Long id);
 @Query("select e from Entry e join fetch e.race where e.horse.id = :id and e.race.raceDate < :date and e.finishPosition is not null and e.status='FINISHED' and e.race.status='OFFICIAL'")
 List<Entry> past(Long id, LocalDate date);
 @Query("select e from Entry e join fetch e.horse where e.horse.id in :ids and e.race.raceDate < :date and e.finishPosition is not null and e.status='FINISHED' and e.race.status='OFFICIAL'")
 List<Entry> pastForHorses(java.util.Set<Long> ids, LocalDate date);

 @Query("select e from Entry e join fetch e.horse join fetch e.race where e.horse.id in :ids and e.finishPosition is not null and e.status='FINISHED' and e.race.status='OFFICIAL' and e.race.raceDate <= :today order by e.race.raceDate desc, e.race.id desc, e.number asc")
 List<Entry> findForComparison(java.util.Set<Long> ids,LocalDate today);
 @Query("select e.race.id, e.winOdds from Entry e where e.race.id in :ids and e.status not in ('SCRATCHED','VOID')")
 List<Object[]> oddsByRace(java.util.Set<Long> ids);
 @Query("select distinct e.jockey from Entry e order by e.jockey") List<String> jockeyNames();
 @EntityGraph(attributePaths={"horse","race"}) List<Entry> findByJockeyOrderByRaceRaceDateDescRaceIdDesc(String name);
 @Query("select e from Entry e join fetch e.horse join fetch e.race where e.race.status='SCHEDULED' and e.status='DECLARED' and e.race.raceDate between :today and :through and not exists (select result.id from Entry result where result.race=e.race and result.finishPosition is not null) and exists (select f.id from Favorite f where f.member.id=:user and f.horse=e.horse) order by e.race.raceDate,e.race.id,e.number")
 List<Entry> upcomingFavoriteHorses(Long user,LocalDate today,LocalDate through);
}
