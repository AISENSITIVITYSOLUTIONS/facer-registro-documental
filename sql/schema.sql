CREATE DATABASE IF NOT EXISTS zona_franca_backend CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE zona_franca_backend;

CREATE TABLE IF NOT EXISTS institutions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    code VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_institutions_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    uuid CHAR(36) NOT NULL,
    first_name VARCHAR(120) NOT NULL,
    last_name VARCHAR(120) NOT NULL,
    institutional_id VARCHAR(100) NOT NULL,
    institution_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_uuid (uuid),
    UNIQUE KEY uq_users_institutional_id (institutional_id),
    KEY idx_users_institution_id (institution_id),
    CONSTRAINT fk_users_institution
        FOREIGN KEY (institution_id) REFERENCES institutions (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS identity_documents (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    uuid CHAR(36) NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    country ENUM('MX', 'CO') NOT NULL,
    document_type ENUM('INE', 'PASSPORT_MX', 'CEDULA_CO', 'PASSPORT_CO') NOT NULL,
    full_name VARCHAR(200) NULL,
    first_name VARCHAR(120) NULL,
    last_name VARCHAR(120) NULL,
    address VARCHAR(255) NULL,
    birth_date DATE NULL,
    sex VARCHAR(20) NULL,
    national_id VARCHAR(50) NULL,
    document_number VARCHAR(50) NULL,
    curp VARCHAR(18) NULL,
    nationality VARCHAR(60) NULL,
    issue_date DATE NULL,
    expiration_date DATE NULL,
    extracted_text_raw TEXT NULL,
    extracted_fields_json JSON NULL,
    extraction_confidence DECIMAL(5,4) NULL,
    validation_status ENUM('pending', 'valid', 'invalid', 'needs_review') NOT NULL DEFAULT 'pending',
    comparison_status ENUM('exact_match', 'high_match', 'medium_match', 'low_match', 'mismatch') NULL,
    comparison_score DECIMAL(5,4) NULL,
    source_image_gcs_path VARCHAR(255) NOT NULL,
    capture_quality_score DECIMAL(5,4) NULL,
    ocr_engine VARCHAR(50) NULL,
    status ENUM('uploaded', 'processing', 'processed', 'confirmed', 'failed') NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_identity_documents_uuid (uuid),
    KEY idx_identity_documents_user_id (user_id),
    KEY idx_identity_documents_status (status),
    KEY idx_identity_documents_validation_status (validation_status),
    CONSTRAINT fk_identity_documents_user
        FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS document_audit_log (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    document_id BIGINT UNSIGNED NOT NULL,
    action VARCHAR(60) NOT NULL,
    details JSON NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_document_audit_log_document_id (document_id),
    CONSTRAINT fk_document_audit_log_document
        FOREIGN KEY (document_id) REFERENCES identity_documents (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
