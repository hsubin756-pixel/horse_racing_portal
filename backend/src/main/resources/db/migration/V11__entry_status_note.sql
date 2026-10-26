-- Preserve the provider's result remark separately from the normalized entry status.
ALTER TABLE entry ADD status_note VARCHAR(30) NULL;
