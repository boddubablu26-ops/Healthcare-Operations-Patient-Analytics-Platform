-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 05_condition_analysis.sql
-- Description: Condition Ranks, Co-Occurrence, and Yearly Prevalences
-- ============================================================================

-- Q16: Dense Ranking of Diagnosed Conditions by Overall Patient Volume
SELECT 
    code,
    description,
    COUNT(DISTINCT patient_id) AS patient_count,
    DENSE_RANK() OVER (ORDER BY COUNT(DISTINCT patient_id) DESC) AS prevalence_rank
FROM raw_synthea.conditions
GROUP BY code, description
ORDER BY prevalence_rank
LIMIT 25;

-- Q20: Window Function - Top 3 Conditions Diagnosed per Calendar Year
WITH annual_conditions AS (
    SELECT 
        EXTRACT(YEAR FROM start_date)::INT AS diagnosis_year,
        description AS condition_name,
        COUNT(DISTINCT patient_id) AS patient_count,
        ROW_NUMBER() OVER (
            PARTITION BY EXTRACT(YEAR FROM start_date) 
            ORDER BY COUNT(DISTINCT patient_id) DESC
        ) AS rank_in_year
    FROM raw_synthea.conditions
    WHERE start_date IS NOT NULL
    GROUP BY EXTRACT(YEAR FROM start_date), description
)
SELECT 
    diagnosis_year,
    rank_in_year,
    condition_name,
    patient_count
FROM annual_conditions
WHERE rank_in_year <= 3
ORDER BY diagnosis_year DESC, rank_in_year;

-- Q29: Clinical Condition Co-Occurrence Pair Frequency
SELECT 
    c1.description AS condition_a,
    c2.description AS condition_b,
    COUNT(DISTINCT c1.patient_id) AS shared_patient_count
FROM raw_synthea.conditions c1
JOIN raw_synthea.conditions c2 ON c1.patient_id = c2.patient_id AND c1.code < c2.code
GROUP BY c1.description, c2.description
HAVING COUNT(DISTINCT c1.patient_id) >= 10
ORDER BY shared_patient_count DESC
LIMIT 20;
