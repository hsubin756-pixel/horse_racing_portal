package dev.keiba;
import java.math.BigDecimal;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
/** 배당 기준 인기 계산 규칙: 낮은 배당이 상위, 같은 배당은 공동 순위, 배당이 없으면 비움. */
class OddsRankTest {
 static BigDecimal d(String v){return new BigDecimal(v);}
 static final List<BigDecimal> FIELD=List.of(d("2.4"),d("4.6"),d("4.6"),d("9.0"));
 @Test void ranksLowestOddsFirstAndSharesTies(){
  var first=CatalogService.oddsRank(d("2.4"),FIELD,4);
  assertEquals(1,first.rank());assertFalse(first.shared());assertEquals(4,first.field());assertEquals(4,first.total());
  var tied=CatalogService.oddsRank(d("4.6"),FIELD,4);
  assertEquals(2,tied.rank());assertTrue(tied.shared());
  assertEquals(4,CatalogService.oddsRank(d("9.0"),FIELD,4).rank());
 }
 @Test void comparesByValueNotScale(){assertEquals(2,CatalogService.oddsRank(d("4.60"),FIELD,4).rank());assertTrue(CatalogService.oddsRank(d("4.60"),FIELD,4).shared());}
 @Test void leavesRankEmptyWithoutOddsButReportsFieldSize(){
  var missing=CatalogService.oddsRank(null,FIELD,5);
  assertNull(missing.rank());assertNull(missing.shared());assertEquals(4,missing.field());assertEquals(5,missing.total());
  var scratched=CatalogService.oddsRank(d("3.0"),null,5);
  assertNull(scratched.rank());assertNull(scratched.field());
  assertNull(CatalogService.oddsRank(d("3.0"),List.of(),0).rank());
 }
}
