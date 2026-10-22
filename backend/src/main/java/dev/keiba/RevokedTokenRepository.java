package dev.keiba;
import org.springframework.data.jpa.repository.JpaRepository;
interface RevokedTokenRepository extends JpaRepository<RevokedToken,String> {}
