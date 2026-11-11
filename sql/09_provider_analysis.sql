-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 09_provider_analysis.sql
-- Description: Clinician Patient Panels, Encounter Volume, and Cost Benchmarks
-- ============================================================================

-- Q10: Providers Treating the Most Unique Patients Across Facilities
SELECT 
    pr.provider_id,
    pr.name AS provider_name,
    pr.specialty,
    org.name AS primary_facility,
    COUNT(DISTINCT e.patient_id) AS unique_patients_treated,
    COUNT(e.encounter_id) AS total_encounters,
    ROUND(AVG(e.total_claim_cost), 2) AS avg_encounter_cost,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (e.stop_time - e.start_time)) / 60)
        FILTER (WHERE e.stop_time IS NOT NULL),
        1
    ) AS avg_encounter_duration_mins
FROM raw_synthea.providers pr
JOIN raw_synthea.organizations org ON pr.organization_id = org.organization_id
LEFT JOIN raw_synthea.encounters e ON pr.provider_id = e.provider_id
GROUP BY pr.provider_id, pr.name, pr.specialty, org.name
HAVING COUNT(e.encounter_id) >= 10
ORDER BY unique_patients_treated DESC
LIMIT 25;
