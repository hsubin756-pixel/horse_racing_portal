package dev.keiba.common;

import java.time.Clock;
import java.time.ZoneId;
import org.springframework.context.annotation.*;

@Configuration
class TimeConfig {

    @Bean
    Clock racingClock() {
        return Clock.system(ZoneId.of("Asia/Tokyo"));
    }
}
