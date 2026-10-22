package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="member")
public class Member {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 String email;
 String passwordHash;
 String nickname;
 protected Member() {}
 Member(String email,String passwordHash,String nickname) { this.email=email;this.passwordHash=passwordHash;this.nickname=nickname; }
}
