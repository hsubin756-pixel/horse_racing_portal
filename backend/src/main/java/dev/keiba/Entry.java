package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="entry")
public class Entry {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="horse_id") Horse horse;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="race_id") Race race;
 int number;
 String jockey;
 Integer finishPosition;
 java.math.BigDecimal timeSeconds;
 protected Entry() {}
}
