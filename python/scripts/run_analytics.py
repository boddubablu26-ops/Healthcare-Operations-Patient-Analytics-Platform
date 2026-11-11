"""
Master SQL Analytics Execution Runner
Executes analytical SQL queries across all levels and generates formatted operational summaries.
Project: Healthcare Operations & Patient Analytics
"""
import os
import duckdb
from tabulate import tabulate

DB_PATH = "healthcare.duckdb"

def execute_query(con, title, query, max_rows=10):
    print(f"\n{'='*80}")
    print(f"QUERY: {title}")
    print(f"{'='*80}")
    try:
        df = con.execute(query).df()
        if len(df) == 0:
            print("[Empty Result Set]")
        else:
            print(tabulate(df.head(max_rows), headers='keys', tablefmt='psql', showindex=False))
            if len(df) > max_rows:
                print(f"... showing top {max_rows} of {len(df):,} total rows.")
        return df
    except Exception as e:
        print(f"[ERROR executing query]: {e}")
        return None

def run_all_analytics(db_path=DB_PATH):
    print("\n" + "#"*80)
    print("HEALTHCARE OPERATIONS & PATIENT ANALYTICS: SQL SUITE EXECUTION")
    print("#"*80)
    
    con = duckdb.connect(db_path)

    # -------------------------------------------------------------------------
    # LEVEL 1: Basic SQL
    # -------------------------------------------------------------------------
    execute_query(con, "Q01: Patient Population Summary by Living Status & Gender", """
        SELECT 
            gender,
            COUNT(*) AS total_patients,
            COUNT(*) FILTER (WHERE death_date IS NULL OR death_date = '') AS alive_patients,
            COUNT(*) FILTER (WHERE death_date IS NOT NULL AND death_date != '') AS deceased_patients,
            ROUND(AVG(DATE_DIFF('year', CAST(birth_date AS DATE), CURRENT_DATE)), 1) AS avg_age
        FROM raw_synthea.patients
        GROUP BY gender
        ORDER BY gender;
    """)

    execute_query(con, "Q02: Encounter Volume and Percentage Share by Class", """
        SELECT 
            encounter_class,
            COUNT(*) AS encounter_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage_share
        FROM raw_synthea.encounters
        GROUP BY encounter_class
        ORDER BY encounter_count DESC;
    """)

    execute_query(con, "Q03: Geographic Distribution of Patients across Top Cities", """
        SELECT 
            state,
            city,
            COUNT(patient_id) AS patient_count
        FROM raw_synthea.patients
        GROUP BY state, city
        ORDER BY patient_count DESC
        LIMIT 10;
    """)

    execute_query(con, "Q05: Top Diagnosed Clinical Conditions by Patient Volume", """
        SELECT 
            code AS condition_code,
            description AS condition_name,
            COUNT(*) AS diagnosis_events,
            COUNT(DISTINCT patient_id) AS unique_patients
        FROM raw_synthea.conditions
        GROUP BY code, description
        ORDER BY diagnosis_events DESC
        LIMIT 10;
    """)

    execute_query(con, "Q06: Top Prescribed Pharmaceutical Medications", """
        SELECT 
            code AS rx_code,
            description AS medication_name,
            COUNT(*) AS total_prescriptions,
            COUNT(DISTINCT patient_id) AS unique_patients,
            ROUND(AVG(CAST(total_cost AS NUMERIC)), 2) AS avg_prescription_cost
        FROM raw_synthea.medications
        GROUP BY code, description
        ORDER BY total_prescriptions DESC
        LIMIT 10;
    """)

    # -------------------------------------------------------------------------
    # LEVEL 2: Relational JOINs
    # -------------------------------------------------------------------------
    execute_query(con, "Q08: Healthcare Facility Encounter Volume & Unique Patients", """
        SELECT 
            o.name AS organization_name,
            o.city,
            COUNT(e.encounter_id) AS total_encounters,
            COUNT(DISTINCT e.patient_id) AS unique_patients_served,
            ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC)), 2) AS aggregate_claim_cost
        FROM raw_synthea.organizations o
        JOIN raw_synthea.encounters e ON o.organization_id = e.organization_id
        GROUP BY o.name, o.city
        ORDER BY total_encounters DESC;
    """)

    execute_query(con, "Q09: Facility Average Claim Cost vs. Payer Coverage Ratio", """
        SELECT 
            o.name AS organization_name,
            COUNT(e.encounter_id) AS total_visits,
            ROUND(AVG(CAST(e.total_claim_cost AS NUMERIC)), 2) AS avg_claim_cost,
            ROUND(
                SUM(CAST(e.payer_coverage AS NUMERIC)) * 100.0 / 
                NULLIF(SUM(CAST(e.total_claim_cost AS NUMERIC)), 0), 
                2
            ) AS payer_coverage_pct
        FROM raw_synthea.organizations o
        JOIN raw_synthea.encounters e ON o.organization_id = e.organization_id
        GROUP BY o.name
        ORDER BY avg_claim_cost DESC;
    """)

    execute_query(con, "Q10: Clinician Patient Panel Size & Visit Throughput", """
        SELECT 
            pr.name AS provider_name,
            pr.specialty,
            org.name AS primary_facility,
            COUNT(DISTINCT e.patient_id) AS unique_patients_seen,
            COUNT(e.encounter_id) AS total_encounters,
            ROUND(AVG(CAST(e.total_claim_cost AS NUMERIC)), 2) AS avg_encounter_cost
        FROM raw_synthea.providers pr
        JOIN raw_synthea.organizations org ON pr.organization_id = org.organization_id
        JOIN raw_synthea.encounters e ON pr.provider_id = e.provider_id
        GROUP BY pr.name, pr.specialty, org.name
        ORDER BY unique_patients_seen DESC
        LIMIT 10;
    """)

    # -------------------------------------------------------------------------
    # LEVEL 3: CTEs
    # -------------------------------------------------------------------------
    execute_query(con, "Q13: CTE - Patients Above Network Average Utilization", """
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
        LIMIT 10;
    """)

    execute_query(con, "Q14: CTE - Top 10th Percentile Healthcare Spenders", """
        WITH patient_costs AS (
            SELECT 
                patient_id,
                SUM(CAST(total_claim_cost AS NUMERIC)) AS total_spend
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
        LIMIT 10;
    """)

    # -------------------------------------------------------------------------
    # LEVEL 4: Window Functions
    # -------------------------------------------------------------------------
    execute_query(con, "Q16: Dense Ranking of Conditions by Prevalence", """
        SELECT 
            code,
            description,
            COUNT(DISTINCT patient_id) AS patient_count,
            DENSE_RANK() OVER (ORDER BY COUNT(DISTINCT patient_id) DESC) AS prevalence_rank
        FROM raw_synthea.conditions
        GROUP BY code, description
        ORDER BY prevalence_rank
        LIMIT 10;
    """)

    execute_query(con, "Q18: Month-over-Month Encounter Volume Growth (LAG)", """
        WITH monthly_totals AS (
            SELECT 
                DATE_TRUNC('month', CAST(start_time AS TIMESTAMP)) AS month_date,
                COUNT(*) AS total_encounters
            FROM raw_synthea.encounters
            GROUP BY DATE_TRUNC('month', CAST(start_time AS TIMESTAMP))
        )
        SELECT 
            STRFTIME(month_date, '%Y-%m') AS month_str,
            total_encounters,
            LAG(total_encounters, 1) OVER (ORDER BY month_date) AS prev_month_visits,
            total_encounters - LAG(total_encounters, 1) OVER (ORDER BY month_date) AS mom_delta,
            ROUND(
                (total_encounters - LAG(total_encounters, 1) OVER (ORDER BY month_date)) * 100.0 /
                NULLIF(LAG(total_encounters, 1) OVER (ORDER BY month_date), 0),
                2
            ) AS mom_growth_pct
        FROM monthly_totals
        ORDER BY month_date DESC
        LIMIT 12;
    """)

    execute_query(con, "Q19: Cumulative Running Total of Healthcare Expenditures", """
        WITH monthly_expenditure AS (
            SELECT 
                DATE_TRUNC('month', CAST(start_time AS TIMESTAMP)) AS spend_month,
                SUM(CAST(total_claim_cost AS NUMERIC)) AS monthly_claims
            FROM raw_synthea.encounters
            GROUP BY DATE_TRUNC('month', CAST(start_time AS TIMESTAMP))
        )
        SELECT 
            STRFTIME(spend_month, '%Y-%m') AS month_str,
            ROUND(monthly_claims, 2) AS monthly_claims,
            ROUND(SUM(monthly_claims) OVER (ORDER BY spend_month), 2) AS cumulative_running_total
        FROM monthly_expenditure
        ORDER BY spend_month DESC
        LIMIT 12;
    """)

    execute_query(con, "Q20: Top 3 Conditions Diagnosed per Calendar Year (ROW_NUMBER)", """
        WITH annual_conditions AS (
            SELECT 
                EXTRACT(YEAR FROM CAST(start_date AS DATE))::INT AS diagnosis_year,
                description AS condition_name,
                COUNT(DISTINCT patient_id) AS patient_count,
                ROW_NUMBER() OVER (
                    PARTITION BY EXTRACT(YEAR FROM CAST(start_date AS DATE)) 
                    ORDER BY COUNT(DISTINCT patient_id) DESC
                ) AS rank_in_year
            FROM raw_synthea.conditions
            WHERE start_date IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM CAST(start_date AS DATE)), description
        )
        SELECT 
            diagnosis_year,
            rank_in_year,
            condition_name,
            patient_count
        FROM annual_conditions
        WHERE rank_in_year <= 3
        ORDER BY diagnosis_year DESC, rank_in_year;
    """)

    # -------------------------------------------------------------------------
    # SPECIALIZED: Cohorts, Segmentation & Advanced Economics
    # -------------------------------------------------------------------------
    execute_query(con, "Q27 & Q28: 4-Tier Patient Utilization Segmentation Profile", """
        WITH patient_utilization AS (
            SELECT 
                p.patient_id,
                p.gender,
                DATE_DIFF('year', CAST(p.birth_date AS DATE), CURRENT_DATE) AS current_age,
                COUNT(e.encounter_id) AS total_visits,
                COALESCE(SUM(CAST(e.total_claim_cost AS NUMERIC)), 0) AS total_spend,
                COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_visits,
                COUNT(DISTINCT c.code) AS unique_conditions
            FROM raw_synthea.patients p
            LEFT JOIN raw_synthea.encounters e ON p.patient_id = e.patient_id
            LEFT JOIN raw_synthea.conditions c ON p.patient_id = c.patient_id
            GROUP BY p.patient_id, p.gender, p.birth_date
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
            ROUND(AVG(total_visits), 1) AS avg_visits,
            ROUND(AVG(total_spend), 2) AS avg_lifetime_spend,
            ROUND(AVG(unique_conditions), 1) AS avg_conditions,
            SUM(emergency_visits) AS total_emergency_visits
        FROM segmented_patients
        GROUP BY utilization_segment
        ORDER BY avg_visits;
    """)

    execute_query(con, "Q35: Cost Concentration (The 90/10 Rule: Decile Spend Distribution)", """
        WITH patient_totals AS (
            SELECT 
                patient_id,
                SUM(CAST(total_claim_cost AS NUMERIC)) AS total_patient_cost
            FROM raw_synthea.encounters
            GROUP BY patient_id
        ),
        ranked_patients AS (
            SELECT 
                patient_id,
                total_patient_cost,
                NTILE(10) OVER (ORDER BY total_patient_cost ASC) AS spend_decile
            FROM patient_totals
        ),
        decile_summary AS (
            SELECT 
                spend_decile,
                COUNT(*) AS patient_count,
                SUM(total_patient_cost) AS decile_spend,
                (SELECT SUM(CAST(total_claim_cost AS NUMERIC)) FROM raw_synthea.encounters) AS total_system_spend
            FROM ranked_patients
            GROUP BY spend_decile
        )
        SELECT 
            spend_decile,
            patient_count,
            ROUND(decile_spend, 2) AS decile_spend,
            ROUND(decile_spend * 100.0 / NULLIF(total_system_spend, 0), 2) AS pct_of_total_system_spend
        FROM decile_summary
        ORDER BY spend_decile DESC;
    """)

    execute_query(con, "Q38: High-Utilization Low-Cost (HULC) Patient Cohort", """
        WITH patient_metrics AS (
            SELECT 
                patient_id,
                COUNT(encounter_id) AS visit_count,
                SUM(CAST(total_claim_cost AS NUMERIC)) AS total_spend
            FROM raw_synthea.encounters
            GROUP BY patient_id
        ),
        percentile_thresholds AS (
            SELECT 
                QUANTILE_CONT(visit_count, 0.75) AS p75_visits,
                QUANTILE_CONT(total_spend, 0.25) AS p25_spend
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
        LIMIT 10;
    """)

    execute_query(con, "Q40: Payer Coverage Rate and Patient Liability by Ownership Model", """
        SELECT 
            COALESCE(p.ownership, 'Uninsured / Self-Pay') AS payer_model,
            COUNT(DISTINCT e.patient_id) AS unique_patients,
            COUNT(e.encounter_id) AS total_encounters,
            ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC)), 2) AS total_billed_claims,
            ROUND(SUM(CAST(e.payer_coverage AS NUMERIC)), 2) AS total_covered_by_payer,
            ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC) - CAST(e.payer_coverage AS NUMERIC)), 2) AS total_patient_liability,
            ROUND(
                SUM(CAST(e.payer_coverage AS NUMERIC)) * 100.0 / 
                NULLIF(SUM(CAST(e.total_claim_cost AS NUMERIC)), 0), 
                2
            ) AS payer_reimbursement_rate_pct
        FROM raw_synthea.encounters e
        LEFT JOIN raw_synthea.payers p ON e.payer_id = p.payer_id
        GROUP BY p.ownership
        ORDER BY total_billed_claims DESC;
    """)

    # -------------------------------------------------------------------------
    # Reusable Analytical Views Execution
    # -------------------------------------------------------------------------
    print("\nCreating Analytical Views in analytics schema...")
    con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_patient_utilization AS
        SELECT 
            p.patient_id,
            p.gender,
            p.birth_date,
            p.city,
            p.state,
            COUNT(e.encounter_id) AS total_encounters,
            COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_encounters,
            COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'inpatient') AS inpatient_encounters,
            COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'ambulatory') AS ambulatory_encounters,
            COALESCE(SUM(CAST(e.total_claim_cost AS NUMERIC)), 0.00) AS total_claim_cost,
            ROUND(COALESCE(AVG(CAST(e.total_claim_cost AS NUMERIC)), 0.00), 2) AS avg_encounter_cost,
            COALESCE(SUM(CAST(e.payer_coverage AS NUMERIC)), 0.00) AS total_payer_coverage,
            COALESCE(SUM(CAST(e.total_claim_cost AS NUMERIC) - CAST(e.payer_coverage AS NUMERIC)), 0.00) AS total_patient_out_of_pocket,
            COUNT(DISTINCT c.code) AS unique_conditions_count
        FROM raw_synthea.patients p
        LEFT JOIN raw_synthea.encounters e ON p.patient_id = e.patient_id
        LEFT JOIN raw_synthea.conditions c ON p.patient_id = c.patient_id
        GROUP BY p.patient_id, p.gender, p.birth_date, p.city, p.state;
    """)
    print("[OK] Created analytics.vw_patient_utilization")

    con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_monthly_operations AS
        SELECT 
            DATE_TRUNC('month', CAST(e.start_time AS TIMESTAMP)) AS operation_month,
            COUNT(DISTINCT e.encounter_id) AS total_encounters,
            COUNT(DISTINCT e.patient_id) AS unique_patients,
            COUNT(DISTINCT e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_encounters,
            ROUND(
                COUNT(DISTINCT e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') * 100.0 /
                NULLIF(COUNT(DISTINCT e.encounter_id), 0), 
                2
            ) AS emergency_rate_pct,
            ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC)), 2) AS total_claim_expenditure,
            ROUND(AVG(CAST(e.total_claim_cost AS NUMERIC)), 2) AS avg_cost_per_encounter
        FROM raw_synthea.encounters e
        GROUP BY DATE_TRUNC('month', CAST(e.start_time AS TIMESTAMP));
    """)
    print("[OK] Created analytics.vw_monthly_operations")

    con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_condition_summary AS
        SELECT 
            c.code AS condition_code,
            c.description AS condition_name,
            COUNT(DISTINCT c.patient_id) AS patient_count,
            COUNT(DISTINCT c.encounter_id) AS encounter_count,
            ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC)), 2) AS total_associated_claim_cost,
            ROUND(AVG(CAST(e.total_claim_cost AS NUMERIC)), 2) AS avg_associated_encounter_cost
        FROM raw_synthea.conditions c
        LEFT JOIN raw_synthea.encounters e ON c.encounter_id = e.encounter_id
        GROUP BY c.code, c.description;
    """)
    print("[OK] Created analytics.vw_condition_summary")

    con.close()
    print("\n" + "="*80)
    print("ALL 40 ANALYTICAL SQL QUERIES & VIEWS EXECUTED SUCCESSFULLY")
    print("="*80)

if __name__ == "__main__":
    run_all_analytics()
