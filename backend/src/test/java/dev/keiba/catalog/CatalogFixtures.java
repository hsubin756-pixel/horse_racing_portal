package dev.keiba.catalog;

import java.time.LocalDate;

/**
 * 단위 테스트용 엔티티 생성기.
 * 엔티티 필드는 catalog 패키지 안에서만 쓸 수 있으므로, 다른 패키지(분석·관심 목록 등)의 테스트는
 * DB 없이 이 클래스로 Horse·Race·Entry를 만듭니다. 운영 코드에는 포함되지 않습니다(test 소스셋).
 */
public final class CatalogFixtures {
 private CatalogFixtures() {}

 public static Horse horse(long id,String name) {
  var horse=new Horse(); horse.id=id; horse.name=name; return horse;
 }
 public static Horse withParents(Horse horse,Horse sire,Horse dam) {
  horse.sire=sire; horse.dam=dam; return horse;
 }
 public static Race race(long id,String name,LocalDate date) {
  var race=new Race(); race.id=id; race.name=name; race.raceDate=date; return race;
 }
 public static Race officialRace(long id,String name,LocalDate date,int distance,String surface) {
  var race=race(id,name,date); race.status="OFFICIAL"; race.distance=distance; race.surface=surface; return race;
 }
 public static Entry entry(Race race,Horse horse,int number,String jockey,Integer finishPosition) {
  var entry=new Entry(); entry.race=race; entry.horse=horse; entry.number=number; entry.jockey=jockey; entry.finishPosition=finishPosition; return entry;
 }
 public static Entry entry(Race race,Horse horse) { return entry(race,horse,1,null,null); }
}
