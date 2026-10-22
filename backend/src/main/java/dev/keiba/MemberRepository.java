package dev.keiba;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
interface MemberRepository extends JpaRepository<Member,Long> {
 Optional<Member> findByEmail(String email);
 boolean existsByEmail(String email);
}
