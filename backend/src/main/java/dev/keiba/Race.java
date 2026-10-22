package dev.keiba;
import jakarta.persistence.*;
@Entity @Table(name="race")
public class Race {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) Long id;
 String name;
 java.time.LocalDate raceDate;
 String venue;
 int distance;
 String surface;
 protected Race() {}
}
