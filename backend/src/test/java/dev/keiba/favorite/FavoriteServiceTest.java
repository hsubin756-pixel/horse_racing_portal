package dev.keiba.favorite;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import dev.keiba.catalog.CatalogFixtures;
import dev.keiba.catalog.CatalogService;
import dev.keiba.common.ApiException;
import dev.keiba.member.MemberRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/** 즐겨찾기는 항상 인증된 회원 ID로만 조회·변경되는지 확인합니다. */
class FavoriteServiceTest {

    FavoriteRepository favorites;
    MemberRepository members;
    CatalogService catalog;
    FavoriteService service;

    @BeforeEach
    void setUp() {
        favorites = mock(FavoriteRepository.class);
        members = mock(MemberRepository.class);
        catalog = mock(CatalogService.class);
        service = new FavoriteService(favorites, members, catalog);
    }

    @Test
    void addLinksTheAuthenticatedMemberAndTheHorse() {
        var member = mock(dev.keiba.member.Member.class);
        var horse = CatalogFixtures.horse(5L, "가상마");
        when(members.findById(7L)).thenReturn(Optional.of(member));
        when(catalog.requireHorse(5L)).thenReturn(horse);
        service.add(7L, 5L);
        var captor = ArgumentCaptor.forClass(Favorite.class);
        verify(favorites).saveAndFlush(captor.capture());
        assertSame(member, captor.getValue().member);
        assertSame(horse, captor.getValue().horse);
    }

    @Test
    void addRejectsDuplicateWith409() {
        when(favorites.existsByMemberIdAndHorseId(7L, 5L)).thenReturn(true);
        assertEquals(409, assertThrows(ApiException.class, () -> service.add(7L, 5L)).status());
        verify(favorites, never()).saveAndFlush(any());
    }

    @Test
    void addRejectsMissingHorseWith404() {
        when(members.findById(7L)).thenReturn(Optional.of(mock(dev.keiba.member.Member.class)));
        when(catalog.requireHorse(999L)).thenThrow(new ApiException(404, "경주마를 찾을 수 없습니다."));
        assertEquals(404, assertThrows(ApiException.class, () -> service.add(7L, 999L)).status());
        verify(favorites, never()).saveAndFlush(any());
    }

    @Test
    void addForDeletedMemberAsksToLogInAgain() {
        when(members.findById(7L)).thenReturn(Optional.empty());
        assertEquals(401, assertThrows(ApiException.class, () -> service.add(7L, 5L)).status());
    }

    @Test
    void removeIsScopedToTheMember() {
        // 삭제 조건에 회원 ID가 함께 들어가므로 다른 회원의 즐겨찾기 행은 지워지지 않습니다.
        service.remove(7L, 5L);
        verify(favorites).deleteByMemberIdAndHorseId(7L, 5L);
        verify(favorites, never()).deleteById(any());
    }

    @Test
    void listReadsOnlyTheMembersRows() {
        service.list(7L);
        verify(favorites).findByMemberIdOrderByIdDesc(7L);
        verifyNoMoreInteractions(favorites);
    }
}
