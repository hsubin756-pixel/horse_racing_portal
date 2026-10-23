package dev.keiba;
import java.time.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class WatchlistServiceTest {
 @Test void mergesWatchedSourcesAndUsesRacingTimezone(){
  // UTC is still Oct 21 while Japan/Korea is already Oct 22.
  var clock=Clock.fixed(Instant.parse("2026-10-21T16:00:00Z"),ZoneId.of("Asia/Tokyo"));
  var today=LocalDate.of(2026,10,22);var through=today.plusDays(90);
  var races=mock(RaceRepository.class);var entries=mock(EntryRepository.class);var catalog=mock(CatalogService.class);
  var race=new Race();race.id=8L;race.raceDate=today;race.name="Race";
  var horse=new Horse();horse.id=22L;horse.name="Horse";
  var entry=new Entry();entry.race=race;entry.horse=horse;
  when(races.upcomingSaved(1L,today,through)).thenReturn(List.of(race));
  when(entries.upcomingFavoriteHorses(1L,today,through)).thenReturn(List.of(entry));
  when(catalog.view(race)).thenReturn(new CatalogService.RaceView(8L,"Race",today,"Venue",1600,"잔디",null,null,null,null,"SCHEDULED","synthetic_fixture"));
  var service=new WatchlistService(mock(RaceFavoriteRepository.class),mock(MemberRepository.class),catalog,entries,races,clock);
  var result=service.schedule(1L);
  assertEquals(today,result.asOfDate());assertEquals(1,result.races().size());assertTrue(result.races().getFirst().savedRace());
  assertEquals(22L,result.races().getFirst().favoriteHorses().getFirst().id());
  verify(races).upcomingSaved(1L,today,through);verify(entries).upcomingFavoriteHorses(1L,today,through);
 }
}
