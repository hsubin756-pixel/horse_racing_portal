package dev.keiba;
import java.time.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class AnalyticsServiceTest {
 final LocalDate today=LocalDate.of(2026,10,22);
 Entry start(long id,String date,int distance,String surface,Integer finish) {
  var race=new Race();race.id=id;race.status="OFFICIAL";race.name="Fixture "+id;race.raceDate=LocalDate.parse(date);race.distance=distance;race.surface=surface;
  var horse=new Horse();horse.id=22L;horse.name="Horse";
  var entry=new Entry();entry.race=race;entry.horse=horse;entry.finishPosition=finish;entry.number=1;entry.jockey="Jockey";return entry;
 }
 List<Entry> starts(){return List.of(start(1,"2026-01-01",1600,"잔디",1),start(2,"2026-02-01",1600,"잔디",3),start(3,"2026-03-01",2000,"더트",4),start(4,"2026-11-01",1600,"잔디",1),start(5,"2026-04-01",1600,"잔디",null));}
 @Test void excludesFutureAndUnfinishedAndCalculatesRates(){
  var result=AnalyticsService.summarize(starts(),AnalyticsService.filter(null,null,null,null),today);
  assertEquals(3,result.totals().starts());assertEquals(1,result.totals().wins());assertEquals(2,result.totals().top3());
  assertEquals(100.0/3,result.totals().winRate(),.00001);assertEquals(8.0/3,result.totals().averageFinish(),.00001);
  assertEquals(List.of(3L,2L,1L),result.recent().stream().map(AnalyticsService.Recent::raceId).toList());
  assertEquals(List.of("1600","2000"),result.byDistance().stream().map(AnalyticsService.Breakdown::condition).toList());
 }
 @Test void combinesFiltersAndIncludesDateBoundaries(){
  var result=AnalyticsService.summarize(starts(),AnalyticsService.filter(1600,"잔디",LocalDate.of(2026,2,1),LocalDate.of(2026,2,1)),today);
  assertEquals(1,result.totals().starts());assertEquals(3,result.totals().bestFinish());assertEquals(100.0,result.totals().top3Rate());
 }
 @Test void emptySampleHasUnknownRates(){
  var result=AnalyticsService.summarize(starts(),AnalyticsService.filter(2400,null,null,null),today);
  assertEquals(0,result.totals().starts());assertNull(result.totals().winRate());assertNull(result.totals().averageFinish());assertTrue(result.recent().isEmpty());
 }
 @Test void recentFiveAreOrderedWithStableDateTies(){
  var rows=new ArrayList<Entry>();for(int i=1;i<=7;i++)rows.add(start(i,"2026-01-01",1600,"잔디",i));
  var result=AnalyticsService.summarize(rows,AnalyticsService.filter(null,null,null,null),today);
  assertEquals(7,result.totals().starts());assertEquals(List.of(7L,6L,5L,4L,3L),result.recent().stream().map(AnalyticsService.Recent::raceId).toList());
 }
 @Test void rejectsInvalidFilters(){
  assertThrows(ApiException.class,()->AnalyticsService.filter(0,null,null,null));
  assertThrows(ApiException.class,()->AnalyticsService.filter(null,"unknown",null,null));
  assertThrows(ApiException.class,()->AnalyticsService.filter(null,null,today,today.minusDays(1)));
 }
}
