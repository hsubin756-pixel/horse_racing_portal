package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="horse")
public class Horse {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 @Column(nullable=false) String name;
 String kraId;
 String sex;
 java.time.LocalDate birthDate;
 String color;
 String trainer;
 Long trainerId;
 String source;
 String nameEn;
 String origin;
 String breed;
 String kraRank;
 String ownerName;
 String ancestorKey;
 @Column(columnDefinition="json") String profileJson;
 java.time.Instant profileAsOf;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="sire_id") Horse sire;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="dam_id") Horse dam;
 protected Horse() {}
}
