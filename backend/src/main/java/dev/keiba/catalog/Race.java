package dev.keiba.catalog;

import jakarta.persistence.*;

@Entity
@Table(name = "race")
public class Race {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    Long id;

    String name;
    java.time.LocalDate raceDate;
    String venue;
    int distance;
    String surface;
    java.time.LocalTime startTime;
    String raceClass;
    String weather;
    String going;
    String status = "SCHEDULED";
    String source;

    protected Race() {}

    // 다른 패키지(분석·예측·관심 목록)는 필드 대신 읽기 전용 getter로 접근합니다.
    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public java.time.LocalDate getRaceDate() {
        return raceDate;
    }

    public String getVenue() {
        return venue;
    }

    public int getDistance() {
        return distance;
    }

    public String getSurface() {
        return surface;
    }

    public java.time.LocalTime getStartTime() {
        return startTime;
    }

    public String getRaceClass() {
        return raceClass;
    }

    public String getWeather() {
        return weather;
    }

    public String getGoing() {
        return going;
    }

    public String getStatus() {
        return status;
    }

    public String getSource() {
        return source;
    }
}
