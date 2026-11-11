-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 05_views.sql
-- Description: Standardized Reusable Analytical Views
-- ============================================================================

-- 1. Patient Utilization & Economic Profile View
CREATE OR REPLACE VIEW analytics.vw_patient_utilization AS
SELECT 
    p.patient_id,
    p.gender,
    p.birth_date,
    p.city,
    p.state,
    COUNT(e.encounter_id) AS total_encounters,
    COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_encounters,
    COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'inpatient') AS inpatient_encounters,
    COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'ambulatory') AS ambulatory_encounters,
    COALESCE(SUM(e.total_claim_cost), 0.00) AS total_claim_cost,
    ROUND(COALESCE(AVG(e.total_claim_cost), 0.00), 2) AS avg_encounter_cost,
    COALESCE(SUM(e.payer_coverage), 0.00) AS total_payer_coverage,
    COALESCE(SUM(e.total_claim_cost - e.payer_coverage), 0.00) AS total_patient_out_of_pocket,
    COUNT(DISTINCT c.code) AS unique_conditions_count,
    CASE 
        WHEN COUNT(e.encounter_id) <= 1 THEN 'Low (1 Visit)'
        WHEN COUNT(e.encounter_id) BETWEEN 2 AND 4 THEN 'Moderate (2-4 Visits)'
        WHEN COUNT(e.encounter_id) BETWEEN 5 AND 9 THEN 'High (5-9 Visits)'
        ELSE 'Super-Utilizer (10+ Visits)'
    END AS utilization_tier
FROM raw_synthea.patients p
LEFT JOIN raw_synthea.encounters e ON p.patient_id = e.patient_id
LEFT JOIN raw_synthea.conditions c ON p.patient_id = c.patient_id
GROUP BY p.patient_id, p.gender, p.birth_date, p.city, p.state;

-- 2. Monthly Hospital Operational Throughput View
CREATE OR REPLACE VIEW analytics.vw_monthly_operations AS
SELECT 
    DATE_TRUNC('month', e.start_time)::DATE AS operation_month,
    COUNT(DISTINCT e.encounter_id) AS total_encounters,
    COUNT(DISTINCT e.patient_id) AS unique_patients,
    COUNT(DISTINCT e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_encounters,
    ROUND(
        COUNT(DISTINCT e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') * 100.0 /
        NULLIF(COUNT(DISTINCT e.encounter_id), 0), 
        2
    ) AS emergency_rate_pct,
    ROUND(SUM(e.total_claim_cost), 2) AS total_claim_expenditure,
    ROUND(AVG(e.total_claim_cost), 2) AS avg_cost_per_encounter,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (e.stop_time - e.start_time)) / 60)
        FILTER (WHERE e.stop_time IS NOT NULL),
        2
    ) AS avg_encounter_duration_mins
FROM raw_synthea.encounters e
GROUP BY DATE_TRUNC('month', e.start_time);

-- 3. Clinical Condition Aggregate Footprint View
CREATE OR REPLACE VIEW analytics.vw_condition_summary AS
SELECT 
    c.code AS condition_code,
    c.description AS condition_name,
    COUNT(DISTINCT c.patient_id) AS patient_count,
    COUNT(DISTINCT c.encounter_id) AS encounter_count,
    ROUND(SUM(e.total_claim_cost), 2) AS total_associated_claim_cost,
    ROUND(AVG(e.total_claim_cost), 2) AS avg_associated_encounter_cost
FROM raw_synthea.conditions c
LEFT JOIN raw_synthea.encounters e ON c.encounter_id = e.encounter_id
GROUP BY c.code, c.description;

-- 4. Provider Operational Capacity Benchmarks View
CREATE OR REPLACE VIEW analytics.vw_provider_performance AS
SELECT 
    pr.provider_id,
    pr.name AS provider_name,
    pr.gender,
    pr.specialty,
    org.name AS primary_facility_name,
    COUNT(DISTINCT e.patient_id) AS unique_patients_served,
    COUNT(e.encounter_id) AS total_encounters_handled,
    ROUND(AVG(e.total_claim_cost), 2) AS avg_encounter_cost,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (e.stop_time - e.start_time)) / 60)
        FILTER (WHERE e.stop_time IS NOT NULL),
        2
    ) AS avg_visit_duration_mins
FROM raw_synthea.providers pr
JOIN raw_synthea.organizations org ON pr.organization_id = org.organization_id
LEFT JOIN raw_synthea.encounters e ON pr.provider_id = e.provider_id
GROUP BY pr.provider_id, pr.name, pr.gender, pr.specialty, org.name;
