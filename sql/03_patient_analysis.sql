-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 03_patient_analysis.sql
-- Description: Patient-Level Utilization, Above-Average Intensity & Top Deciles
-- ============================================================================

-- Q07: Encounter Intensity and Lifetime Claim Cost per Patient
SELECT 
    p.patient_id,
    p.gender,
    p.city,
    COUNT(e.encounter_id) AS total_encounters,
    COALESCE(SUM(e.total_claim_cost), 0.00) AS total_lifetime_claim_cost
FROM raw_synthea.patients p
LEFT JOIN raw_synthea.encounters e ON p.patient_id = e.patient_id
GROUP BY p.patient_id, p.gender, p.city
ORDER BY total_encounters DESC
LIMIT 50;

-- Q13: Multi-Stage CTE - Patients with Healthcare Utilization Above the Population Mean
WITH patient_counts AS (
    SELECT 
        p.patient_id,
        p.gender,
        COUNT(e.encounter_id) AS visit_count
    FROM raw_synthea.patients p
    LEFT JOIN raw_synthea.encounters e ON p.patient_id = e.patient_id
    GROUP BY p.patient_id, p.gender
),
benchmark AS (
    SELECT AVG(visit_count) AS avg_visits FROM patient_counts
)
SELECT 
    pc.patient_id,
    pc.gender,
    pc.visit_count,
    ROUND(b.avg_visits, 2) AS population_avg_visits,
    ROUND(pc.visit_count - b.avg_visits, 2) AS variance_from_avg
FROM patient_counts pc
CROSS JOIN benchmark b
WHERE pc.visit_count > b.avg_visits
ORDER BY pc.visit_count DESC
LIMIT 50;

-- Q14: Multi-Stage CTE - Patients Whose Healthcare Spending is in the Top 10th Percentile
WITH patient_costs AS (
    SELECT 
        patient_id,
        SUM(total_claim_cost) AS total_spend
    FROM raw_synthea.encounters
    GROUP BY patient_id
),
ranked_patients AS (
    SELECT 
        patient_id,
        total_spend,
        PERCENT_RANK() OVER (ORDER BY total_spend) AS cost_percentile
    FROM patient_costs
)
SELECT 
    patient_id,
    ROUND(total_spend, 2) AS total_spend,
    ROUND((cost_percentile * 100)::NUMERIC, 2) AS percentile_rank
FROM ranked_patients
WHERE cost_percentile >= 0.90
ORDER BY total_spend DESC
LIMIT 50;
