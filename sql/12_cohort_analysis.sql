-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 12_cohort_analysis.sql
-- Description: Patient Acquisition Cohorts & Multi-Tier Utilization Segmentation
-- ============================================================================

-- Q25 & Q26: First-Visit Acquisition Cohorts & Longitudinal Monthly Activity
WITH patient_first_visit AS (
    SELECT 
        patient_id,
        DATE_TRUNC('month', MIN(start_time))::DATE AS cohort_month
    FROM raw_synthea.encounters
    GROUP BY patient_id
),
patient_activity AS (
    SELECT 
        e.patient_id,
        pfv.cohort_month,
        DATE_TRUNC('month', e.start_time)::DATE AS activity_month,
        (EXTRACT(YEAR FROM e.start_time) - EXTRACT(YEAR FROM pfv.cohort_month)) * 12 +
        (EXTRACT(MONTH FROM e.start_time) - EXTRACT(MONTH FROM pfv.cohort_month)) AS period_month_number
    FROM raw_synthea.encounters e
    JOIN patient_first_visit pfv ON e.patient_id = pfv.patient_id
)
SELECT 
    cohort_month,
    COUNT(DISTINCT patient_id) AS total_cohort_patients,
    COUNT(DISTINCT CASE WHEN period_month_number = 0 THEN patient_id END) AS month_0_active,
    COUNT(DISTINCT CASE WHEN period_month_number = 1 THEN patient_id END) AS month_1_active,
    COUNT(DISTINCT CASE WHEN period_month_number = 2 THEN patient_id END) AS month_2_active,
    COUNT(DISTINCT CASE WHEN period_month_number = 3 THEN patient_id END) AS month_3_active,
    COUNT(DISTINCT CASE WHEN period_month_number = 6 THEN patient_id END) AS month_6_active,
    COUNT(DISTINCT CASE WHEN period_month_number = 12 THEN patient_id END) AS month_12_active
FROM patient_activity
GROUP BY cohort_month
ORDER BY cohort_month
LIMIT 24;

-- Q27 & Q28: 4-Tier Patient Utilization Segmentation Profile
WITH patient_utilization AS (
    SELECT 
        p.patient_id,
        p.gender,
        EXTRACT(YEAR FROM AGE(COALESCE(p.death_date, CURRENT_DATE), p.birth_date))::INT AS current_age,
        COUNT(e.encounter_id) AS total_visits,
        COALESCE(SUM(e.total_claim_cost), 0) AS total_spend,
        COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_visits,
        COUNT(DISTINCT c.code) AS unique_conditions
    FROM raw_synthea.patients p
    LEFT JOIN raw_synthea.encounters e ON p.patient_id = e.patient_id
    LEFT JOIN raw_synthea.conditions c ON p.patient_id = c.patient_id
    GROUP BY p.patient_id, p.gender, p.birth_date, p.death_date
),
segmented_patients AS (
    SELECT 
        *,
        CASE 
            WHEN total_visits <= 1 THEN 'Low (1 Visit)'
            WHEN total_visits BETWEEN 2 AND 4 THEN 'Moderate (2-4 Visits)'
            WHEN total_visits BETWEEN 5 AND 9 THEN 'High (5-9 Visits)'
            ELSE 'Super-Utilizer (10+ Visits)'
        END AS utilization_segment
    FROM patient_utilization
)
SELECT 
    utilization_segment,
    COUNT(*) AS patient_count,
    ROUND(AVG(current_age), 1) AS avg_age,
    ROUND(AVG(total_visits), 1) AS avg_visits_per_patient,
    ROUND(AVG(total_spend), 2) AS avg_lifetime_spend,
    ROUND(AVG(unique_conditions), 1) AS avg_conditions_count,
    SUM(emergency_visits) AS total_emergency_visits
FROM segmented_patients
GROUP BY utilization_segment
ORDER BY avg_visits_per_patient;
