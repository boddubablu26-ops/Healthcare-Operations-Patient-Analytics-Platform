-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 01_data_quality.sql
-- Description: Automated Data Quality & Referential Integrity Verification
-- ============================================================================

CREATE TABLE IF NOT EXISTS analytics.data_quality_log (
    check_id SERIAL PRIMARY KEY,
    check_name VARCHAR(100) NOT NULL,
    check_category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    failed_records_count BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    execution_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);

TRUNCATE TABLE analytics.data_quality_log;

-- 1. Uniqueness: Duplicate Patient IDs
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Duplicate Patient IDs',
    'Uniqueness',
    'CRITICAL',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Repeated patient_id records detected in patients table'
FROM (
    SELECT patient_id, COUNT(*) 
    FROM raw_synthea.patients 
    GROUP BY patient_id 
    HAVING COUNT(*) > 1
) sub;

-- 2. Uniqueness: Duplicate Encounter IDs
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Duplicate Encounter IDs',
    'Uniqueness',
    'CRITICAL',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Repeated encounter_id records detected in encounters table'
FROM (
    SELECT encounter_id, COUNT(*) 
    FROM raw_synthea.encounters 
    GROUP BY encounter_id 
    HAVING COUNT(*) > 1
) sub;

-- 3. Completeness: Missing Primary Keys or Start Time
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Null Encounter Primary Keys or Start Time',
    'Completeness',
    'CRITICAL',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Encounters missing encounter_id or start_time'
FROM raw_synthea.encounters
WHERE encounter_id IS NULL OR start_time IS NULL;

-- 4. Temporal Validity: Encounter Stop Time before Start Time
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Encounter End Prior to Start',
    'Temporal Validity',
    'CRITICAL',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Encounters where stop_time < start_time'
FROM raw_synthea.encounters
WHERE stop_time IS NOT NULL AND stop_time < start_time;

-- 5. Temporal Validity: Condition End Date before Start Date
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Condition End Prior to Start',
    'Temporal Validity',
    'HIGH',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Conditions where end_date < start_date'
FROM raw_synthea.conditions
WHERE end_date IS NOT NULL AND end_date < start_date;

-- 6. Financial Validity: Negative Encounter Costs
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Negative Encounter Costs',
    'Financial Validity',
    'HIGH',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Encounters with negative base cost, claim cost, or coverage'
FROM raw_synthea.encounters
WHERE base_encounter_cost < 0 OR total_claim_cost < 0 OR payer_coverage < 0;

-- 7. Financial Validity: Payer Coverage Exceeds Total Claim Cost
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Payer Coverage Exceeds Claim Cost',
    'Financial Validity',
    'MEDIUM',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Encounters where payer_coverage > total_claim_cost + 0.01'
FROM raw_synthea.encounters
WHERE payer_coverage > total_claim_cost + 0.01;

-- 8. Referential Integrity: Orphan Encounters
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Orphan Encounters (Invalid Patient)',
    'Referential Integrity',
    'CRITICAL',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Encounters pointing to non-existent patient_id'
FROM raw_synthea.encounters e
LEFT JOIN raw_synthea.patients p ON e.patient_id = p.patient_id
WHERE p.patient_id IS NULL;

-- 9. Referential Integrity: Orphan Conditions
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Orphan Conditions (Invalid Encounter)',
    'Referential Integrity',
    'CRITICAL',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Conditions pointing to non-existent encounter_id'
FROM raw_synthea.conditions c
LEFT JOIN raw_synthea.encounters e ON c.encounter_id = e.encounter_id
WHERE e.encounter_id IS NULL;

-- 10. Referential Integrity: Orphan Medications
INSERT INTO analytics.data_quality_log (check_name, check_category, severity, failed_records_count, status, details)
SELECT 
    'Orphan Medications (Invalid Patient)',
    'Referential Integrity',
    'CRITICAL',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASSED' ELSE 'FAILED' END,
    'Medications pointing to non-existent patient_id'
FROM raw_synthea.medications m
LEFT JOIN raw_synthea.patients p ON m.patient_id = p.patient_id
WHERE p.patient_id IS NULL;

-- Summary Scorecard
SELECT 
    check_id,
    check_category,
    check_name,
    severity,
    failed_records_count,
    status
FROM analytics.data_quality_log
ORDER BY check_id;
