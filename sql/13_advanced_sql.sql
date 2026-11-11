-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 13_advanced_sql.sql
-- Description: Advanced Operational Scenarios & Multidimensional Economics
-- ============================================================================

-- Q37: Organizations with Increasing Encounter Volume but Decreasing Average Cost
-- Identifies facilities achieving operational economies of scale
WITH facility_monthly AS (
    SELECT 
        organization_id,
        DATE_TRUNC('month', start_time)::DATE AS visit_month,
        COUNT(*) AS encounter_count,
        AVG(total_claim_cost) AS avg_cost
    FROM raw_synthea.encounters
    GROUP BY organization_id, DATE_TRUNC('month', start_time)
),
facility_lagged AS (
    SELECT 
        fm.organization_id,
        org.name AS facility_name,
        fm.visit_month,
        fm.encounter_count,
        LAG(fm.encounter_count) OVER (
            PARTITION BY fm.organization_id ORDER BY fm.visit_month
        ) AS prev_month_volume,
        fm.avg_cost,
        LAG(fm.avg_cost) OVER (
            PARTITION BY fm.organization_id ORDER BY fm.visit_month
        ) AS prev_month_avg_cost
    FROM facility_monthly fm
    JOIN raw_synthea.organizations org ON fm.organization_id = org.organization_id
)
SELECT 
    facility_name,
    visit_month,
    encounter_count,
    prev_month_volume,
    encounter_count - prev_month_volume AS volume_increase,
    ROUND(avg_cost::NUMERIC, 2) AS current_avg_cost,
    ROUND(prev_month_avg_cost::NUMERIC, 2) AS prev_avg_cost,
    ROUND((avg_cost - prev_month_avg_cost)::NUMERIC, 2) AS cost_reduction
FROM facility_lagged
WHERE encounter_count > prev_month_volume 
  AND avg_cost < prev_month_avg_cost
  AND prev_month_volume IS NOT NULL
ORDER BY volume_increase DESC
LIMIT 25;

-- Q38: High-Utilization Low-Cost (HULC) Patient Cohort Identification
-- Patients who visit frequently (top quartile) but generate modest costs (bottom quartile)
WITH patient_metrics AS (
    SELECT 
        patient_id,
        COUNT(encounter_id) AS visit_count,
        SUM(total_claim_cost) AS total_spend
    FROM raw_synthea.encounters
    GROUP BY patient_id
),
percentile_thresholds AS (
    SELECT 
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY visit_count) AS p75_visits,
        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY total_spend) AS p25_spend
    FROM patient_metrics
)
SELECT 
    pm.patient_id,
    p.gender,
    p.city,
    pm.visit_count,
    ROUND(pm.total_spend, 2) AS total_spend,
    ROUND(pm.total_spend / NULLIF(pm.visit_count, 0), 2) AS avg_cost_per_visit
FROM patient_metrics pm
JOIN raw_synthea.patients p ON pm.patient_id = p.patient_id
CROSS JOIN percentile_thresholds pt
WHERE pm.visit_count >= pt.p75_visits 
  AND pm.total_spend <= pt.p25_spend
ORDER BY pm.visit_count DESC
LIMIT 30;

-- Q39: High-Cost Low-Utilization (HCLU) Crisis Cohort
-- Patients with 1-2 visits that generated catastrophic hospital claims (> 90th percentile)
WITH patient_metrics AS (
    SELECT 
        patient_id,
        COUNT(encounter_id) AS visit_count,
        SUM(total_claim_cost) AS total_spend
    FROM raw_synthea.encounters
    GROUP BY patient_id
),
spend_p90 AS (
    SELECT PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY total_spend) AS p90_spend
    FROM patient_metrics
)
SELECT 
    pm.patient_id,
    p.gender,
    pm.visit_count,
    ROUND(pm.total_spend, 2) AS catastrophic_spend,
    ROUND(sp.p90_spend::NUMERIC, 2) AS network_p90_spend_threshold
FROM patient_metrics pm
JOIN raw_synthea.patients p ON pm.patient_id = p.patient_id
CROSS JOIN spend_p90 sp
WHERE pm.visit_count <= 2 
  AND pm.total_spend >= sp.p90_spend
ORDER BY pm.total_spend DESC
LIMIT 30;

-- Q40: Payer Coverage Discrepancy & Out-of-Pocket Liabilities by Payer Ownership Model
SELECT 
    COALESCE(p.ownership, 'Uninsured / Self-Pay') AS payer_ownership_model,
    COUNT(DISTINCT e.patient_id) AS unique_patients,
    COUNT(e.encounter_id) AS total_encounters,
    ROUND(SUM(e.total_claim_cost), 2) AS total_billed_claims,
    ROUND(SUM(e.payer_coverage), 2) AS total_covered_by_payer,
    ROUND(SUM(e.total_claim_cost - e.payer_coverage), 2) AS total_patient_liability,
    ROUND(
        SUM(e.payer_coverage) * 100.0 / NULLIF(SUM(e.total_claim_cost), 0),
        2
    ) AS payer_reimbursement_rate_pct
FROM raw_synthea.encounters e
LEFT JOIN raw_synthea.payers p ON e.payer_id = p.payer_id
GROUP BY p.ownership
ORDER BY total_billed_claims DESC;
