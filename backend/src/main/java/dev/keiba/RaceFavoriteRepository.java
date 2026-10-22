package dev.keiba;
import java.util.List;
import org.springframework.data.jpa.repository.*;
interface RaceFavoriteRepository extends JpaRepository<RaceFavorite,Long> {
 @EntityGraph(attributePaths="race") List<RaceFavorite> findByMemberIdOrderByRaceRaceDateAscRaceIdAsc(Long id);
 boolean existsByMemberIdAndRaceId(Long member,Long race);
 void deleteByMemberIdAndRaceId(Long member,Long race);
}
