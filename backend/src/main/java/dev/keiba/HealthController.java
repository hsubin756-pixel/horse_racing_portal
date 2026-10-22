package dev.keiba;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.dao.DataAccessException;
import org.springframework.web.bind.annotation.*;
@RestController
class HealthController {
 final JdbcTemplate jdbc;
 HealthController(JdbcTemplate jdbc) { this.jdbc=jdbc; }
 @GetMapping("/api/health") Map<String,String> health() {
  try { jdbc.queryForObject("SELECT 1",Integer.class); }
  catch(DataAccessException error) { throw new ApiException(503,"데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도하세요."); }
  return Map.of("status","ok");
 }
}
