package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="horse")
public class Horse {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 @Column(nullable=false) String name;
 String sex;
 java.time.LocalDate birthDate;
 String color;
 String trainer;
 Long trainerId;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="sire_id") Horse sire;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="dam_id") Horse dam;
 protected Horse() {}
}
