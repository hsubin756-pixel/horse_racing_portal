package dev.keiba;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.domain.*;
interface HorseRepository extends JpaRepository<Horse,Long> {
 @org.springframework.data.jpa.repository.EntityGraph(attributePaths={"sire","dam"})
 Page<Horse> findByNameContainingIgnoreCase(String name, Pageable pageable);
}
