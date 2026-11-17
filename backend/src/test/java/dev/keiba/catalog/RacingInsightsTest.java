package dev.keiba.catalog;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class RacingInsightsTest {

    @Test
    void classifiesRelativeEarlyPosition() {
        assertEquals("선행", RacingInsights.classify(1, 12));
        assertEquals("선입", RacingInsights.classify(4, 12));
        assertEquals("중단", RacingInsights.classify(8, 12));
        assertEquals("추입", RacingInsights.classify(9, 12));
        assertEquals("선입", RacingInsights.classify(2, 5));
        assertEquals("추입", RacingInsights.classify(5, 5));
    }

    @Test
    void withholdsMissingImpossibleOrSoloPositions() {
        for (Integer p : new Integer[] { null, 0, 13 }) {
            assertEquals("판단 보류", RacingInsights.classify(p, 12));
        }
        assertEquals("판단 보류", RacingInsights.classify(1, 1));
    }
}
