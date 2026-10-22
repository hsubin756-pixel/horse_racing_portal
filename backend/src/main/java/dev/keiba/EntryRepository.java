package dev.keiba;
import java.util.List;
import java.time.LocalDate;
import org.springframework.data.jpa.repository.*;
interface EntryRepository extends JpaRepository<Entry,Long> {
 @EntityGraph(attributePaths={"horse","race"})
 List<Entry> findByHorseIdOrderByRaceRaceDateDesc(Long id);
 @EntityGraph(attributePaths={"horse","race"})
 List<Entry> findByRaceIdOrderByNumberAsc(Long id);
 @Query("select e from Entry e join fetch e.race where e.horse.id = :id and e.race.raceDate < :date and e.finishPosition is not null")
 List<Entry> past(Long id, LocalDate date);
}
