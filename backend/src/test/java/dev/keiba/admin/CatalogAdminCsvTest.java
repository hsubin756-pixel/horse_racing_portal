package dev.keiba.admin;

import static org.junit.jupiter.api.Assertions.*;

import dev.keiba.common.ApiException;
import org.junit.jupiter.api.Test;

class CatalogAdminCsvTest {

    @Test
    void csvSupportsQuotedCommasNewlinesBOMAndEscapedQuotes() {
        var rows = CatalogAdmin.parseCsv("\uFEFFname,biography\r\n\"가상, 기수\",\"첫 줄\n두 번째 \"\"인용\"\"\"\r\n");
        assertEquals(1, rows.size());
        assertEquals("가상, 기수", rows.getFirst().get("name"));
        assertEquals("첫 줄\n두 번째 \"인용\"", rows.getFirst().get("biography"));
    }

    @Test
    void csvRejectsMalformedRowsAndDoesNotDropTrailingEmptyCells() {
        assertNull(CatalogAdmin.parseCsv("a,b\n1,").getFirst().get("missing"));
        assertEquals("", CatalogAdmin.parseCsv("a,b\n1,").getFirst().get("b"));
        for (String csv : new String[] { "a,a\n1,2", "a,b\n1", "a\n\"unclosed", "a\n\"closed\"oops" }) {
            assertThrows(ApiException.class, () -> CatalogAdmin.parseCsv(csv));
        }
    }
}
