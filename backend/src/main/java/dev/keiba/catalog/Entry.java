package dev.keiba.catalog;

import jakarta.persistence.*;

@Entity
@Table(name = "entry")
public class Entry {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "horse_id")
    Horse horse;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "race_id")
    Race race;

    int number;
    String jockey;
    Long jockeyId;
    Long trainerId;
    String trainerName;
    Integer finishPosition;
    java.math.BigDecimal timeSeconds;
    Integer popularityRank;

    @Column(precision = 7, scale = 1)
    java.math.BigDecimal winOdds;

    String oddsSource;
    java.time.Instant oddsAsOf;
    Integer gate;
    java.math.BigDecimal carriedWeight;
    Integer bodyWeight;
    Integer weightChange;
    String status = "FINISHED";
    String statusNote;

    protected Entry() {}

    // 다른 패키지(분석·예측·관심 목록)는 필드 대신 읽기 전용 getter로 접근합니다.
    public Long getId() {
        return id;
    }

    public Horse getHorse() {
        return horse;
    }

    public Race getRace() {
        return race;
    }

    public int getNumber() {
        return number;
    }

    public String getJockey() {
        return jockey;
    }

    public Long getJockeyId() {
        return jockeyId;
    }

    public Long getTrainerId() {
        return trainerId;
    }

    public String getTrainerName() {
        return trainerName;
    }

    public Integer getFinishPosition() {
        return finishPosition;
    }

    public java.math.BigDecimal getTimeSeconds() {
        return timeSeconds;
    }

    public Integer getPopularityRank() {
        return popularityRank;
    }

    public java.math.BigDecimal getWinOdds() {
        return winOdds;
    }

    public String getOddsSource() {
        return oddsSource;
    }

    public java.time.Instant getOddsAsOf() {
        return oddsAsOf;
    }

    public Integer getGate() {
        return gate;
    }

    public java.math.BigDecimal getCarriedWeight() {
        return carriedWeight;
    }

    public Integer getBodyWeight() {
        return bodyWeight;
    }

    public Integer getWeightChange() {
        return weightChange;
    }

    public String getStatus() {
        return status;
    }

    public String getStatusNote() {
        return statusNote;
    }
}
