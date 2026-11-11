-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 11_time_series.sql
-- Description: Time-Series Trends, Moving Averages & Seasonal Patterns
-- ============================================================================

-- Q21: Monthly Emergency vs. Ambulatory Visit Trend
SELECT 
    DATE_TRUNC('month', start_time)::DATE AS visit_month,
    COUNT(*) AS total_encounters,
    COUNT(*) FILTER (WHERE encounter_class = 'emergency') AS emergency_encounters,
    COUNT(*) FILTER (WHERE encounter_class = 'ambulatory') AS ambulatory_encounters,
    COUNT(*) FILTER (WHERE encounter_class = 'wellness') AS wellness_encounters,
    ROUND(
        COUNT(*) FILTER (WHERE encounter_class = 'emergency') * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS emergency_ratio_pct
FROM raw_synthea.encounters
GROUP BY DATE_TRUNC('month', start_time)
ORDER BY visit_month;

-- Q22: 3-Month Moving Average of Healthcare Claim Costs
WITH monthly_claims AS (
    SELECT 
        DATE_TRUNC('month', start_time)::DATE AS spend_month,
        SUM(total_claim_cost) AS total_spend
    FROM raw_synthea.encounters
    GROUP BY DATE_TRUNC('month', start_time)
)
SELECT 
    spend_month,
    ROUND(total_spend, 2) AS monthly_spend,
    ROUND(
        AVG(total_spend) OVER (
            ORDER BY spend_month 
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 
        2
    ) AS moving_avg_3mo_spend
FROM monthly_claims
ORDER BY spend_month;

-- Q23: Seasonal Variation in Healthcare Utilization by Month of Year
SELECT 
    TO_CHAR(start_time, 'Month') AS month_name,
    EXTRACT(MONTH FROM start_time)::INT AS month_num,
    COUNT(*) AS total_encounters,
    ROUND(AVG(total_claim_cost), 2) AS avg_encounter_cost
FROM raw_synthea.encounters
GROUP BY TO_CHAR(start_time, 'Month'), EXTRACT(MONTH FROM start_time)
ORDER BY month_num;
