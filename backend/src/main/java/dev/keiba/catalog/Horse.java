package dev.keiba.catalog;
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

 // 다른 패키지(분석·예측·관심 목록)는 필드 대신 읽기 전용 getter로 접근합니다.
 public Long getId() { return id; }
 public String getName() { return name; }
 public String getKraId() { return kraId; }
 public String getSex() { return sex; }
 public java.time.LocalDate getBirthDate() { return birthDate; }
 public String getColor() { return color; }
 public String getTrainer() { return trainer; }
 public Long getTrainerId() { return trainerId; }
 public String getSource() { return source; }
 public String getNameEn() { return nameEn; }
 public String getOrigin() { return origin; }
 public String getBreed() { return breed; }
 public String getKraRank() { return kraRank; }
 public String getOwnerName() { return ownerName; }
 public String getAncestorKey() { return ancestorKey; }
 public String getProfileJson() { return profileJson; }
 public java.time.Instant getProfileAsOf() { return profileAsOf; }
 public Horse getSire() { return sire; }
 public Horse getDam() { return dam; }
}
