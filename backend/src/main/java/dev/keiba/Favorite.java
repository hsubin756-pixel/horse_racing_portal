package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="favorite")
public class Favorite {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="member_id") Member member;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="horse_id") Horse horse;
 protected Favorite() {}
 Favorite(Member member,Horse horse) { this.member=member; this.horse=horse; }
}
