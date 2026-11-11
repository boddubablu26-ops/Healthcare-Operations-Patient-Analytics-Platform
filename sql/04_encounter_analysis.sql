-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 04_encounter_analysis.sql
-- Description: Encounter Throughput, Length of Stay & MoM Growth
-- ============================================================================

-- Q18: Month-over-Month Encounter Volume Growth & Variance
WITH monthly_totals AS (
    SELECT 
        DATE_TRUNC('month', start_time)::DATE AS month_date,
        COUNT(*) AS total_encounters
    FROM raw_synthea.encounters
    GROUP BY DATE_TRUNC('month', start_time)
)
SELECT 
    month_date,
    total_encounters,
    LAG(total_encounters, 1) OVER (ORDER BY month_date) AS prev_month_encounters,
    total_encounters - LAG(total_encounters, 1) OVER (ORDER BY month_date) AS mom_encounter_change,
    ROUND(
        (total_encounters - LAG(total_encounters, 1) OVER (ORDER BY month_date)) * 100.0 /
        NULLIF(LAG(total_encounters, 1) OVER (ORDER BY month_date), 0),
        2
    ) AS mom_growth_pct
FROM monthly_totals
ORDER BY month_date;

-- Encounter Duration Distribution by Class (Mean, Median, p90)
SELECT 
    encounter_class,
    COUNT(*) AS total_visits,
    ROUND(AVG(EXTRACT(EPOCH FROM (stop_time - start_time))/60)::NUMERIC, 1) AS avg_duration_mins,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (stop_time - start_time))/60)::NUMERIC, 1) AS median_duration_mins,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (stop_time - start_time))/60)::NUMERIC, 1) AS p90_duration_mins
FROM raw_synthea.encounters
WHERE stop_time IS NOT NULL
GROUP BY encounter_class
ORDER BY total_visits DESC;
