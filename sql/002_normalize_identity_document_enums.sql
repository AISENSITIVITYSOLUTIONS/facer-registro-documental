UPDATE identity_documents
SET validation_status = CASE validation_status
    WHEN 'PENDING' THEN 'pending'
    WHEN 'VALID' THEN 'valid'
    WHEN 'INVALID' THEN 'invalid'
    WHEN 'NEEDS_REVIEW' THEN 'needs_review'
    ELSE validation_status
END;

UPDATE identity_documents
SET comparison_status = CASE comparison_status
    WHEN 'EXACT_MATCH' THEN 'exact_match'
    WHEN 'HIGH_MATCH' THEN 'high_match'
    WHEN 'MEDIUM_MATCH' THEN 'medium_match'
    WHEN 'LOW_MATCH' THEN 'low_match'
    WHEN 'MISMATCH' THEN 'mismatch'
    ELSE comparison_status
END
WHERE comparison_status IS NOT NULL;

UPDATE identity_documents
SET status = CASE status
    WHEN 'UPLOADED' THEN 'uploaded'
    WHEN 'PROCESSING' THEN 'processing'
    WHEN 'PROCESSED' THEN 'processed'
    WHEN 'CONFIRMED' THEN 'confirmed'
    WHEN 'FAILED' THEN 'failed'
    ELSE status
END;
