package dev.keiba;
import java.time.LocalDate;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.domain.*;
interface RaceRepository extends JpaRepository<Race,Long> {
 @Query("select r from Race r where lower(r.name) like lower(concat('%',:q,'%')) and (:date is null or r.raceDate = :date)")
 Page<Race> search(String q, LocalDate date, Pageable pageable);
}
