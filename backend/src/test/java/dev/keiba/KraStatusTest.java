package dev.keiba;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class KraStatusTest {
 @Test void separatesTaskCountsFromRaceCountsAndOmitsLocalPaths() throws Exception {
  var state=new ObjectMapper().readTree("""
  {"calls":602,"tasks":{"1:20261010":{"site":"보류 있음","training":"수집 완료","archive":"/private/key","races":{"1":{"error":"ord: 착순 미제공"},"2":{"status":"반영 완료"}}},"2:20261010":{"site":"자료 없음","training":"수집 완료"}}}
  """);
  var summary=KraStatusController.summarize("20260726-20261025-123",state);
  assertEquals(2,summary.get("tasks"));assertEquals(1,summary.get("siteCompleted"));
  assertEquals(1,summary.get("heldRaces"));assertEquals(1,summary.get("importedRaces"));
  assertFalse(summary.toString().contains("/private"));
  assertFalse(KraStatusController.safeError("https://provider?key=secret").contains("secret"));
 }
}
