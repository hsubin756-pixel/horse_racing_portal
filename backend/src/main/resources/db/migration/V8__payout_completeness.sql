-- Explicit NULL checks are required: MySQL CHECK also accepts UNKNOWN.
ALTER TABLE payout ADD CONSTRAINT ck_payout_completeness CHECK (
 (status='OPEN' AND odds IS NOT NULL AND amount_yen IS NULL)
 OR (status IN ('FINAL','REFUND') AND odds IS NULL AND amount_yen IS NOT NULL)
);
