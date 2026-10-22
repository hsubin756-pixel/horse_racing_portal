package dev.keiba;
import java.util.List;
import org.springframework.data.jpa.repository.*;
interface FavoriteRepository extends JpaRepository<Favorite,Long> {
 @EntityGraph(attributePaths="horse") List<Favorite> findByMemberIdOrderByIdDesc(Long memberId);
 boolean existsByMemberIdAndHorseId(Long memberId,Long horseId);
 void deleteByMemberIdAndHorseId(Long memberId,Long horseId);
}
