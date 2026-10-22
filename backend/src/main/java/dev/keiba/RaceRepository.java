package dev.keiba;
import java.time.LocalDate;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.domain.*;
interface RaceRepository extends JpaRepository<Race,Long> {
 Page<Race> findByNameContainingIgnoreCase(String q, Pageable pageable);
 Page<Race> findByNameContainingIgnoreCaseAndRaceDate(String q, LocalDate date, Pageable pageable);
 default Page<Race> search(String q,LocalDate date,Pageable pageable) {
  return date==null ? findByNameContainingIgnoreCase(q,pageable) : findByNameContainingIgnoreCaseAndRaceDate(q,date,pageable);
 }

 @Query("select r from Race r where r.raceDate between :today and :through and exists (select f.id from RaceFavorite f where f.member.id=:user and f.race=r) and not exists (select e.id from Entry e where e.race=r and e.finishPosition is not null)")
 java.util.List<Race> upcomingSaved(Long user,LocalDate today,LocalDate through);
}
