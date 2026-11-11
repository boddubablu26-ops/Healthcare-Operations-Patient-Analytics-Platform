-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 10_organization_analysis.sql
-- Description: Hospital Facility Throughput, Cost Benchmarks, and Monthly Ranks
-- ============================================================================

-- Q08: Hospital Facility Encounter Throughput and Patient Reach
SELECT 
    o.organization_id,
    o.name AS organization_name,
    o.city,
    COUNT(e.encounter_id) AS total_encounters,
    COUNT(DISTINCT e.patient_id) AS unique_patients_served,
    COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_visits,
    ROUND(SUM(e.total_claim_cost), 2) AS aggregate_claim_revenue
FROM raw_synthea.organizations o
JOIN raw_synthea.encounters e ON o.organization_id = e.organization_id
GROUP BY o.organization_id, o.name, o.city
ORDER BY total_encounters DESC;

-- Q15: Organizations Whose Average Encounter Cost Exceeds Network Mean
WITH network_benchmark AS (
    SELECT AVG(total_claim_cost) AS network_avg_cost FROM raw_synthea.encounters
),
facility_stats AS (
    SELECT 
        o.organization_id,
        o.name AS organization_name,
        COUNT(e.encounter_id) AS total_visits,
        AVG(e.total_claim_cost) AS facility_avg_cost
    FROM raw_synthea.organizations o
    JOIN raw_synthea.encounters e ON o.organization_id = e.organization_id
    GROUP BY o.organization_id, o.name
    HAVING COUNT(e.encounter_id) >= 20
)
SELECT 
    f.organization_name,
    f.total_visits,
    ROUND(f.facility_avg_cost, 2) AS facility_avg_cost,
    ROUND(nb.network_avg_cost, 2) AS network_avg_cost,
    ROUND((f.facility_avg_cost - nb.network_avg_cost), 2) AS cost_variance
FROM facility_stats f
CROSS JOIN network_benchmark nb
WHERE f.facility_avg_cost > nb.network_avg_cost
ORDER BY cost_variance DESC;

-- Q17: Monthly Facility Throughput Ranking Using Window Functions
WITH monthly_facility_encounters AS (
    SELECT 
        DATE_TRUNC('month', start_time)::DATE AS visit_month,
        organization_id,
        COUNT(*) AS monthly_encounters
    FROM raw_synthea.encounters
    GROUP BY DATE_TRUNC('month', start_time), organization_id
)
SELECT 
    mfe.visit_month,
    org.name AS facility_name,
    mfe.monthly_encounters,
    RANK() OVER (PARTITION BY mfe.visit_month ORDER BY mfe.monthly_encounters DESC) AS monthly_rank
FROM monthly_facility_encounters mfe
JOIN raw_synthea.organizations org ON mfe.organization_id = org.organization_id
ORDER BY mfe.visit_month DESC, monthly_rank;
