package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="race_favorite")
class RaceFavorite {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="member_id") Member member;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="race_id") Race race;
 protected RaceFavorite(){}
 RaceFavorite(Member member,Race race){this.member=member;this.race=race;}
}
