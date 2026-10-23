package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="entry")
public class Entry {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="horse_id") Horse horse;
 @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="race_id") Race race;
 int number;
 String jockey;
 Long jockeyId;
 Long trainerId;
 String trainerName;
 Integer finishPosition;
 java.math.BigDecimal timeSeconds;
 Integer popularityRank;
 @Column(precision=7,scale=1) java.math.BigDecimal winOdds;
 String oddsSource;
 java.time.Instant oddsAsOf;
 Integer gate;
 java.math.BigDecimal carriedWeight;
 Integer bodyWeight;
 Integer weightChange;
 String status="FINISHED";
 protected Entry() {}
}
