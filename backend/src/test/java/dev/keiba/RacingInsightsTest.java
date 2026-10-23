package dev.keiba;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class RacingInsightsTest {
 @Test void classifiesRelativeEarlyPosition(){
  assertEquals("선행",RacingInsights.classify(1,12));assertEquals("선입",RacingInsights.classify(4,12));
  assertEquals("중단",RacingInsights.classify(8,12));assertEquals("추입",RacingInsights.classify(9,12));
  assertEquals("선입",RacingInsights.classify(2,5));assertEquals("추입",RacingInsights.classify(5,5));
 }
 @Test void withholdsMissingImpossibleOrSoloPositions(){for(Integer p:new Integer[]{null,0,13})assertEquals("판단 보류",RacingInsights.classify(p,12));assertEquals("판단 보류",RacingInsights.classify(1,1));}
 @Test void csvSupportsQuotedCommasNewlinesBOMAndEscapedQuotes(){
  var rows=CatalogAdmin.parseCsv("\uFEFFname,biography\r\n\"가상, 기수\",\"첫 줄\n두 번째 \"\"인용\"\"\"\r\n");
  assertEquals(1,rows.size());assertEquals("가상, 기수",rows.getFirst().get("name"));assertEquals("첫 줄\n두 번째 \"인용\"",rows.getFirst().get("biography"));
 }
 @Test void csvRejectsMalformedRowsAndDoesNotDropTrailingEmptyCells(){
  assertNull(CatalogAdmin.parseCsv("a,b\n1,").getFirst().get("missing"));assertEquals("",CatalogAdmin.parseCsv("a,b\n1,").getFirst().get("b"));
  for(String csv:new String[]{"a,a\n1,2","a,b\n1","a\n\"unclosed","a\n\"closed\"oops"})assertThrows(ApiException.class,()->CatalogAdmin.parseCsv(csv));
 }
}
