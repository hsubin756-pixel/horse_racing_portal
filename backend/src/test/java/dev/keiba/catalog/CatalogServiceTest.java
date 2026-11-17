package dev.keiba.catalog;

import dev.keiba.common.ApiException;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/** 검색 조건 검증, 없는 자료의 404, 3대 혈통 트리(누락·순환·깊이 제한)를 확인합니다. */
class CatalogServiceTest {
 HorseRepository horses; RaceRepository races; EntryRepository entries; CatalogService service;

 @BeforeEach void setUp() {
  horses=mock(HorseRepository.class); races=mock(RaceRepository.class); entries=mock(EntryRepository.class);
  service=new CatalogService(horses,races,entries);
 }

 @Test void rejectsUnsupportedSearchOptionsBeforeQuerying() {
  for(Runnable call:new Runnable[]{
   ()->service.horses("",0,"password","asc"),
   ()->service.horses("",0,"name","sideways"),
   ()->service.horses("",-1,"name","asc"),
   ()->service.horses("x".repeat(101),0,"name","asc"),
   ()->service.races("",null,-1)}) {
   assertEquals(400,assertThrows(ApiException.class,call::run).status());
  }
  verifyNoInteractions(horses,races);
 }

 @Test void missingHorseAndRaceReturn404() {
  when(horses.findById(any())).thenReturn(Optional.empty());
  when(races.findById(any())).thenReturn(Optional.empty());
  assertEquals(404,assertThrows(ApiException.class,()->service.horse(1L)).status());
  assertEquals(404,assertThrows(ApiException.class,()->service.history(1L)).status());
  assertEquals(404,assertThrows(ApiException.class,()->service.race(1L)).status());
  assertEquals(404,assertThrows(ApiException.class,()->service.pedigree(1L)).status());
 }

 @Test void pedigreeKeepsMissingAncestorsAsNull() {
  var grandSire=CatalogFixtures.horse(3L,"조부");
  var sire=CatalogFixtures.withParents(CatalogFixtures.horse(2L,"부"),grandSire,null);
  var horse=CatalogFixtures.withParents(CatalogFixtures.horse(1L,"본마"),sire,null);
  when(horses.findById(1L)).thenReturn(Optional.of(horse));
  var tree=service.pedigree(1L);
  assertEquals("본마",tree.name());
  assertNull(tree.dam(),"모마 정보가 없으면 오류 없이 비어 있어야 합니다");
  assertEquals("부",tree.sire().name());
  assertEquals("조부",tree.sire().sire().name());
  assertNull(tree.sire().dam());
 }

 @Test void pedigreeStopsAtThreeGenerations() {
  // 0세대(본마)부터 5세대까지 부계로 이어진 계보
  Horse ancestor=null;
  for(long generation=5;generation>=0;generation--)
   ancestor=CatalogFixtures.withParents(CatalogFixtures.horse(generation+1,"G"+generation),ancestor,null);
  when(horses.findById(1L)).thenReturn(Optional.of(ancestor));
  var node=service.pedigree(1L);
  for(int generation=0;generation<3;generation++) { assertEquals("G"+generation,node.name()); node=node.sire(); }
  assertEquals("G3",node.name(),"3대(증조)까지 포함합니다");
  assertNull(node.sire(),"4대 이후는 응답하지 않습니다");
 }

 @Test void pedigreeIgnoresCyclesInBadData() {
  var horse=CatalogFixtures.horse(1L,"순환");
  CatalogFixtures.withParents(horse,horse,null);
  when(horses.findById(1L)).thenReturn(Optional.of(horse));
  var tree=service.pedigree(1L);
  assertEquals("순환",tree.name());
  assertNull(tree.sire(),"자기 자신을 조상으로 다시 펼치지 않습니다");
 }
}
