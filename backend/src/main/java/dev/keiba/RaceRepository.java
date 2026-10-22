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
}
