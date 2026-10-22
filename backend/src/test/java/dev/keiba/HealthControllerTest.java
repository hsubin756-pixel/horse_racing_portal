package dev.keiba;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class HealthControllerTest {
 @Test void checksDatabaseReadiness() {
  var jdbc=mock(JdbcTemplate.class);when(jdbc.queryForObject("SELECT 1",Integer.class)).thenReturn(1);
  assertEquals("ok",new HealthController(jdbc).health().get("status"));
  verify(jdbc).queryForObject("SELECT 1",Integer.class);
 }
 @Test void reportsDatabaseOutageAsUnavailable() {
  var jdbc=mock(JdbcTemplate.class);when(jdbc.queryForObject("SELECT 1",Integer.class)).thenThrow(new CannotGetJdbcConnectionException("test"));
  var error=assertThrows(ApiException.class,()->new HealthController(jdbc).health());assertEquals(503,error.status);
 }
}
