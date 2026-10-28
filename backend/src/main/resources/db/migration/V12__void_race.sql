ALTER TABLE race DROP CHECK ck_race_status,
 ADD CONSTRAINT ck_race_status CHECK(status IN ('SCHEDULED','RUNNING','OFFICIAL','CANCELLED','VOID'));
ALTER TABLE entry DROP CHECK ck_entry_state,
 ADD CONSTRAINT ck_entry_state CHECK(status IN ('DECLARED','FINISHED','SCRATCHED','DNF','DISQUALIFIED','VOID')),
 ADD CONSTRAINT ck_void_entry CHECK(status<>'VOID' OR
  (finish_position IS NULL AND time_seconds IS NULL AND win_odds IS NULL AND popularity_rank IS NULL));
