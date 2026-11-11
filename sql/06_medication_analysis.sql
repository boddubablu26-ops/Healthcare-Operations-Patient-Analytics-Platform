-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 06_medication_analysis.sql
-- Description: Medication Prescriptions Mapped to Diagnosis & Expenditures
-- ============================================================================

-- Q12: Medications Co-Prescribed During Encounters for Specific Diagnoses
SELECT 
    c.description AS condition_name,
    m.description AS prescribed_medication,
    COUNT(*) AS co_occurrence_count,
    ROUND(AVG(m.total_cost), 2) AS avg_medication_cost
FROM raw_synthea.conditions c
JOIN raw_synthea.medications m ON c.encounter_id = m.encounter_id
GROUP BY c.description, m.description
HAVING COUNT(*) >= 15
ORDER BY co_occurrence_count DESC
LIMIT 25;

-- Pharmaceutical Expenditure by Payer Coverage Ratio
SELECT 
    m.description AS medication_name,
    COUNT(*) AS prescription_count,
    ROUND(SUM(m.total_cost), 2) AS aggregate_drug_cost,
    ROUND(SUM(m.payer_coverage), 2) AS aggregate_payer_paid,
    ROUND(
        SUM(m.payer_coverage) * 100.0 / NULLIF(SUM(m.total_cost), 0),
        2
    ) AS drug_payer_coverage_pct
FROM raw_synthea.medications m
GROUP BY m.description
HAVING COUNT(*) >= 20
ORDER BY aggregate_drug_cost DESC
LIMIT 20;
