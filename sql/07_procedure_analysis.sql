-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 07_procedure_analysis.sql
-- Description: Clinical Procedures Volume, Setting & Cost Analysis
-- ============================================================================

-- Q31: Procedure Volume and Mean Cost by Encounter Class Setting
SELECT 
    e.encounter_class,
    p.description AS procedure_name,
    COUNT(p.encounter_id) AS procedure_volume,
    COUNT(DISTINCT p.patient_id) AS unique_patients,
    ROUND(AVG(p.base_cost), 2) AS avg_procedure_cost,
    ROUND(SUM(p.base_cost), 2) AS total_procedure_cost
FROM raw_synthea.procedures p
JOIN raw_synthea.encounters e ON p.encounter_id = e.encounter_id
GROUP BY e.encounter_class, p.description
HAVING COUNT(p.encounter_id) >= 10
ORDER BY e.encounter_class, procedure_volume DESC;
