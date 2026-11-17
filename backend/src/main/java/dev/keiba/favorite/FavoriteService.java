package dev.keiba.favorite;

import dev.keiba.catalog.CatalogService;
import dev.keiba.common.ApiException;
import dev.keiba.member.MemberRepository;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
class FavoriteService {

    private final FavoriteRepository favorites;
    private final MemberRepository members;
    private final CatalogService catalog;

    FavoriteService(FavoriteRepository favorites, MemberRepository members, CatalogService catalog) {
        this.favorites = favorites;
        this.members = members;
        this.catalog = catalog;
    }

    @Transactional(readOnly = true)
    List<CatalogService.HorseView> list(Long user) {
        return favorites
            .findByMemberIdOrderByIdDesc(user)
            .stream()
            .map(f -> catalog.view(f.horse))
            .toList();
    }

    void add(Long user, Long horse) {
        if (favorites.existsByMemberIdAndHorseId(user, horse)) {
            throw new ApiException(409, "이미 즐겨찾기에 등록된 경주마입니다.");
        }
        favorites.saveAndFlush(
            new Favorite(
                members.findById(user).orElseThrow(() -> new ApiException(401, "다시 로그인하세요.")),
                catalog.requireHorse(horse)
            )
        );
    }

    void remove(Long user, Long horse) {
        favorites.deleteByMemberIdAndHorseId(user, horse);
    }
}
