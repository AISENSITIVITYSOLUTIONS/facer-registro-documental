ALTER TABLE identity_documents
    ADD COLUMN address VARCHAR(255) NULL AFTER last_name;
