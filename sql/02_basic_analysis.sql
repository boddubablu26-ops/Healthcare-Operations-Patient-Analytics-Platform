-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 02_basic_analysis.sql
-- Description: Level 1 Foundational SQL (Q01 - Q06)
-- ============================================================================

-- Q01: Total patient population summary broken down by living status and gender
SELECT 
    gender,
    COUNT(*) AS total_patients,
    COUNT(*) FILTER (WHERE death_date IS NULL) AS active_alive_patients,
    COUNT(*) FILTER (WHERE death_date IS NOT NULL) AS deceased_patients,
    ROUND(AVG(EXTRACT(YEAR FROM AGE(COALESCE(death_date, CURRENT_DATE), birth_date))), 1) AS avg_age
FROM raw_synthea.patients
GROUP BY gender
ORDER BY gender;

-- Q02: Encounter volume and percentage share across clinical service classes
SELECT 
    encounter_class,
    COUNT(*) AS encounter_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage_share
FROM raw_synthea.encounters
GROUP BY encounter_class
ORDER BY encounter_count DESC;

-- Q03: Geographic patient distribution across states and cities
SELECT 
    state,
    city,
    COUNT(patient_id) AS patient_count
FROM raw_synthea.patients
GROUP BY state, city
ORDER BY patient_count DESC
LIMIT 20;

-- Q04: Top 10 most common clinical reasons recorded for an encounter
SELECT 
    reason_code,
    reason_description,
    COUNT(*) AS visit_count
FROM raw_synthea.encounters
WHERE reason_code IS NOT NULL
GROUP BY reason_code, reason_description
ORDER BY visit_count DESC
LIMIT 10;

-- Q05: Top 15 diagnosed conditions in the synthetic database
SELECT 
    code AS condition_code,
    description AS condition_description,
    COUNT(*) AS diagnosis_events,
    COUNT(DISTINCT patient_id) AS unique_patients_affected
FROM raw_synthea.conditions
GROUP BY code, description
ORDER BY diagnosis_events DESC
LIMIT 15;

-- Q06: Top 15 most frequently prescribed pharmaceutical medications
SELECT 
    code AS rx_code,
    description AS medication_name,
    COUNT(*) AS total_prescriptions,
    COUNT(DISTINCT patient_id) AS patient_count,
    ROUND(AVG(total_cost), 2) AS avg_prescription_cost
FROM raw_synthea.medications
GROUP BY code, description
ORDER BY total_prescriptions DESC
LIMIT 15;
