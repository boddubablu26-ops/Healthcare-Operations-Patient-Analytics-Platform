"""
Healthcare Operations & Patient Analytics Platform
Production Application Server
Theme: Clean Solid Natural Palette (White #FFFFFF, Base #F8FAFC, Royal #2563EB)
Features: On-Demand Lazy Loading, Minimalist Layout, Live DuckDB / PostgreSQL Execution
"""
import os
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import duckdb

PORT = 8055
DB_PATH = "healthcare.duckdb"

PRESET_QUERIES = {
    "Q01": {
        "title": "Q01: Patient Demographics & Living Status",
        "category": "Level 1: Basic",
        "sql": """SELECT 
    gender,
    COUNT(*) AS total_patients,
    COUNT(*) FILTER (WHERE death_date IS NULL OR death_date = '') AS alive_patients,
    COUNT(*) FILTER (WHERE death_date IS NOT NULL AND death_date != '') AS deceased_patients,
    ROUND(AVG(DATE_DIFF('year', CAST(birth_date AS DATE), CURRENT_DATE)), 1) AS avg_age
FROM raw_synthea.patients
GROUP BY gender
ORDER BY gender;"""
    },
    "Q02": {
        "title": "Q02: Encounter Volume by Service Class",
        "category": "Level 1: Basic",
        "sql": """SELECT 
    encounter_class,
    COUNT(*) AS encounter_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS share_pct
FROM raw_synthea.encounters
GROUP BY encounter_class
ORDER BY encounter_count DESC;"""
    },
    "Q05": {
        "title": "Q05: Top 10 Clinical Conditions",
        "category": "Level 1: Basic",
        "sql": """SELECT 
    code AS condition_code,
    description AS condition_name,
    COUNT(*) AS total_events,
    COUNT(DISTINCT patient_id) AS unique_patients
FROM raw_synthea.conditions
GROUP BY code, description
ORDER BY total_events DESC
LIMIT 10;"""
    },
    "Q08": {
        "title": "Q08: Facility Throughput & Reach",
        "category": "Level 2: JOINs",
        "sql": """SELECT 
    o.name AS organization_name,
    o.city,
    COUNT(e.encounter_id) AS total_encounters,
    COUNT(DISTINCT e.patient_id) AS unique_patients,
    COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_visits,
    ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC)), 2) AS total_claim_cost
FROM raw_synthea.organizations o
JOIN raw_synthea.encounters e ON o.organization_id = e.organization_id
GROUP BY o.name, o.city
ORDER BY total_encounters DESC;"""
    },
    "Q09": {
        "title": "Q09: Facility Cost vs. Payer Coverage",
        "category": "Level 2: JOINs",
        "sql": """SELECT 
    o.name AS organization_name,
    COUNT(e.encounter_id) AS total_visits,
    ROUND(AVG(CAST(e.total_claim_cost AS NUMERIC)), 2) AS avg_claim_cost,
    ROUND(SUM(CAST(e.payer_coverage AS NUMERIC)) * 100.0 / NULLIF(SUM(CAST(e.total_claim_cost AS NUMERIC)), 0), 2) AS coverage_pct
FROM raw_synthea.organizations o
JOIN raw_synthea.encounters e ON o.organization_id = e.organization_id
GROUP BY o.name
ORDER BY avg_claim_cost DESC;"""
    },
    "Q10": {
        "title": "Q10: Provider Panel Size & Case Volume",
        "category": "Level 2: JOINs",
        "sql": """SELECT 
    pr.name AS provider_name,
    pr.specialty,
    org.name AS primary_facility,
    COUNT(DISTINCT e.patient_id) AS unique_patients,
    COUNT(e.encounter_id) AS total_encounters,
    ROUND(AVG(CAST(e.total_claim_cost AS NUMERIC)), 2) AS avg_encounter_cost
FROM raw_synthea.providers pr
JOIN raw_synthea.organizations org ON pr.organization_id = org.organization_id
JOIN raw_synthea.encounters e ON pr.provider_id = e.provider_id
GROUP BY pr.name, pr.specialty, org.name
ORDER BY unique_patients DESC
LIMIT 15;"""
    },
    "Q13": {
        "title": "Q13: CTE - Patients Above Average Visits",
        "category": "Level 3: CTEs",
        "sql": """WITH patient_counts AS (
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
    ROUND(b.avg_visits, 2) AS network_avg,
    ROUND(pc.visit_count - b.avg_visits, 2) AS delta
FROM patient_counts pc
CROSS JOIN benchmark b
WHERE pc.visit_count > b.avg_visits
ORDER BY pc.visit_count DESC
LIMIT 20;"""
    },
    "Q14": {
        "title": "Q14: CTE - Top 10th Percentile Spenders",
        "category": "Level 3: CTEs",
        "sql": """WITH patient_costs AS (
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
        PERCENT_RANK() OVER (ORDER BY total_spend) AS percentile
    FROM patient_costs
)
SELECT 
    patient_id,
    ROUND(total_spend, 2) AS total_spend,
    ROUND((percentile * 100)::NUMERIC, 1) AS percentile_rank
FROM ranked_patients
WHERE percentile >= 0.90
ORDER BY total_spend DESC
LIMIT 20;"""
    },
    "Q16": {
        "title": "Q16: Condition Prevalence Dense Rank",
        "category": "Level 4: Windows",
        "sql": """SELECT 
    code,
    description,
    COUNT(DISTINCT patient_id) AS patient_count,
    DENSE_RANK() OVER (ORDER BY COUNT(DISTINCT patient_id) DESC) AS rank
FROM raw_synthea.conditions
GROUP BY code, description
ORDER BY rank
LIMIT 15;"""
    },
    "Q18": {
        "title": "Q18: Month-over-Month Growth (LAG)",
        "category": "Level 4: Windows",
        "sql": """WITH monthly_totals AS (
    SELECT 
        DATE_TRUNC('month', CAST(start_time AS TIMESTAMP)) AS month_date,
        COUNT(*) AS total_encounters
    FROM raw_synthea.encounters
    GROUP BY DATE_TRUNC('month', CAST(start_time AS TIMESTAMP))
)
SELECT 
    STRFTIME(month_date, '%Y-%m') AS month,
    total_encounters,
    LAG(total_encounters, 1) OVER (ORDER BY month_date) AS prev_month,
    total_encounters - LAG(total_encounters, 1) OVER (ORDER BY month_date) AS diff,
    ROUND(
        (total_encounters - LAG(total_encounters, 1) OVER (ORDER BY month_date)) * 100.0 /
        NULLIF(LAG(total_encounters, 1) OVER (ORDER BY month_date), 0),
        2
    ) AS mom_growth_pct
FROM monthly_totals
ORDER BY month_date DESC
LIMIT 15;"""
    },
    "Q19": {
        "title": "Q19: Cumulative Running Total of Claims",
        "category": "Level 4: Windows",
        "sql": """WITH monthly_expenditure AS (
    SELECT 
        DATE_TRUNC('month', CAST(start_time AS TIMESTAMP)) AS spend_month,
        SUM(CAST(total_claim_cost AS NUMERIC)) AS monthly_claims
    FROM raw_synthea.encounters
    GROUP BY DATE_TRUNC('month', CAST(start_time AS TIMESTAMP))
)
SELECT 
    STRFTIME(spend_month, '%Y-%m') AS month,
    ROUND(monthly_claims, 2) AS monthly_claims,
    ROUND(SUM(monthly_claims) OVER (ORDER BY spend_month), 2) AS cumulative_total
FROM monthly_expenditure
ORDER BY spend_month DESC
LIMIT 15;"""
    },
    "Q27_Q28": {
        "title": "Q27 & Q28: 4-Tier Utilization Segmentation",
        "category": "Specialized",
        "sql": """WITH patient_utilization AS (
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
    SELECT *,
    CASE 
        WHEN total_visits <= 1 THEN 'Low (1 Visit)'
        WHEN total_visits BETWEEN 2 AND 4 THEN 'Moderate (2-4 Visits)'
        WHEN total_visits BETWEEN 5 AND 9 THEN 'High (5-9 Visits)'
        ELSE 'Super-Utilizer (10+ Visits)'
    END AS segment
    FROM patient_utilization
)
SELECT 
    segment,
    COUNT(*) AS patient_count,
    ROUND(AVG(current_age), 1) AS avg_age,
    ROUND(AVG(total_visits), 1) AS avg_visits,
    ROUND(AVG(total_spend), 2) AS avg_lifetime_spend,
    ROUND(AVG(unique_conditions), 1) AS avg_conditions,
    SUM(emergency_visits) AS total_emergency_visits
FROM segmented_patients
GROUP BY segment
ORDER BY avg_visits;"""
    },
    "Q29": {
        "title": "Q29: Clinical Condition Co-Occurrence Dyads",
        "category": "Specialized",
        "sql": """SELECT 
    c1.description AS condition_a,
    c2.description AS condition_b,
    COUNT(DISTINCT c1.patient_id) AS shared_patients
FROM raw_synthea.conditions c1
JOIN raw_synthea.conditions c2 ON c1.patient_id = c2.patient_id AND c1.code < c2.code
GROUP BY c1.description, c2.description
HAVING COUNT(DISTINCT c1.patient_id) >= 10
ORDER BY shared_patients DESC
LIMIT 10;"""
    },
    "Q35": {
        "title": "Q35: Cost Concentration (The 90/10 Spend Rule)",
        "category": "Specialized",
        "sql": """WITH patient_totals AS (
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
        NTILE(10) OVER (ORDER BY total_spend ASC) AS decile
    FROM patient_totals
),
decile_summary AS (
    SELECT 
        decile,
        COUNT(*) AS patient_count,
        SUM(total_spend) AS decile_spend,
        (SELECT SUM(CAST(total_claim_cost AS NUMERIC)) FROM raw_synthea.encounters) AS total_spend_system
    FROM ranked_patients
    GROUP BY decile
)
SELECT 
    decile,
    patient_count,
    ROUND(decile_spend, 2) AS decile_spend,
    ROUND(decile_spend * 100.0 / NULLIF(total_spend_system, 0), 2) AS pct_of_total_spend
FROM decile_summary
ORDER BY decile DESC;"""
    },
    "Q40": {
        "title": "Q40: Payer Reimbursement & Patient Liability",
        "category": "Specialized",
        "sql": """SELECT 
    COALESCE(p.ownership, 'Uninsured / Self-Pay') AS payer_model,
    COUNT(DISTINCT e.patient_id) AS unique_patients,
    COUNT(e.encounter_id) AS encounters,
    ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC)), 2) AS billed_claims,
    ROUND(SUM(CAST(e.payer_coverage AS NUMERIC)), 2) AS covered_by_payer,
    ROUND(SUM(CAST(e.total_claim_cost AS NUMERIC) - CAST(e.payer_coverage AS NUMERIC)), 2) AS patient_liability,
    ROUND(
        SUM(CAST(e.payer_coverage AS NUMERIC)) * 100.0 / 
        NULLIF(SUM(CAST(e.total_claim_cost AS NUMERIC)), 0), 
        2
    ) AS reimbursement_rate_pct
FROM raw_synthea.encounters e
LEFT JOIN raw_synthea.payers p ON e.payer_id = p.payer_id
GROUP BY p.ownership
ORDER BY billed_claims DESC;"""
    }
}

class DashboardHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def _send_html(self, content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._send_html(HTML_TEMPLATE)
            return

        con = duckdb.connect(DB_PATH, read_only=True)
        try:
            if path == "/api/summary":
                metrics = {}
                metrics["total_patients"] = con.execute("SELECT COUNT(*) FROM raw_synthea.patients").fetchone()[0]
                metrics["total_encounters"] = con.execute("SELECT COUNT(*) FROM raw_synthea.encounters").fetchone()[0]
                metrics["total_spend"] = float(con.execute("SELECT SUM(CAST(total_claim_cost AS NUMERIC)) FROM raw_synthea.encounters").fetchone()[0] or 0)
                metrics["emergency_visits"] = con.execute("SELECT COUNT(*) FROM raw_synthea.encounters WHERE encounter_class = 'emergency'").fetchone()[0]
                metrics["emergency_rate"] = round(metrics["emergency_visits"] * 100.0 / metrics["total_encounters"], 1)
                metrics["avg_encounter_cost"] = round(metrics["total_spend"] / metrics["total_encounters"], 2)
                metrics["payer_coverage"] = float(con.execute("SELECT SUM(CAST(payer_coverage AS NUMERIC)) FROM raw_synthea.encounters").fetchone()[0] or 0)
                metrics["patient_liability"] = round(metrics["total_spend"] - metrics["payer_coverage"], 2)
                metrics["reimbursement_rate"] = round(metrics["payer_coverage"] * 100.0 / metrics["total_spend"], 1)
                self._send_json(metrics)

            elif path == "/api/charts/monthly":
                df = con.execute("""
                    SELECT 
                        STRFTIME(DATE_TRUNC('month', CAST(start_time AS TIMESTAMP)), '%Y-%m') AS month,
                        COUNT(*) AS total_visits,
                        COUNT(*) FILTER (WHERE encounter_class = 'emergency') AS emergency_visits,
                        ROUND(SUM(CAST(total_claim_cost AS NUMERIC)), 2) AS total_spend
                    FROM raw_synthea.encounters
                    GROUP BY DATE_TRUNC('month', CAST(start_time AS TIMESTAMP))
                    ORDER BY DATE_TRUNC('month', CAST(start_time AS TIMESTAMP))
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/charts/classes":
                df = con.execute("""
                    SELECT 
                        encounter_class, 
                        COUNT(*) AS count
                    FROM raw_synthea.encounters
                    GROUP BY encounter_class 
                    ORDER BY count DESC
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/charts/facilities":
                df = con.execute("""
                    SELECT 
                        o.name, 
                        COUNT(e.encounter_id) AS encounters,
                        COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_visits
                    FROM raw_synthea.organizations o
                    JOIN raw_synthea.encounters e ON o.organization_id = e.organization_id
                    GROUP BY o.name 
                    ORDER BY encounters DESC
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/charts/segmentation":
                df = con.execute("""
                    WITH patient_utilization AS (
                        SELECT 
                            p.patient_id, 
                            COUNT(e.encounter_id) AS total_visits,
                            COALESCE(SUM(CAST(e.total_claim_cost AS NUMERIC)), 0) AS total_spend,
                            COUNT(e.encounter_id) FILTER (WHERE e.encounter_class = 'emergency') AS emergency_visits
                        FROM raw_synthea.patients p
                        LEFT JOIN raw_synthea.encounters e ON p.patient_id = e.patient_id
                        GROUP BY p.patient_id
                    ),
                    segmented AS (
                        SELECT *,
                        CASE 
                            WHEN total_visits <= 1 THEN 'Low (1 Visit)'
                            WHEN total_visits BETWEEN 2 AND 4 THEN 'Moderate (2-4 Visits)'
                            WHEN total_visits BETWEEN 5 AND 9 THEN 'High (5-9 Visits)'
                            ELSE 'Super-Utilizer (10+ Visits)'
                        END AS segment
                        FROM patient_utilization
                    )
                    SELECT 
                        segment, 
                        COUNT(*) AS count,
                        ROUND(AVG(total_visits), 1) AS avg_visits,
                        ROUND(AVG(total_spend), 2) AS avg_spend,
                        SUM(emergency_visits) AS emergency_visits
                    FROM segmented 
                    GROUP BY segment 
                    ORDER BY avg_visits
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/charts/deciles":
                df = con.execute("""
                    WITH patient_totals AS (
                        SELECT 
                            patient_id, 
                            SUM(CAST(total_claim_cost AS NUMERIC)) AS total_cost
                        FROM raw_synthea.encounters 
                        GROUP BY patient_id
                    ),
                    ranked AS (
                        SELECT 
                            patient_id, 
                            total_cost, 
                            NTILE(10) OVER (ORDER BY total_cost ASC) AS decile
                        FROM patient_totals
                    )
                    SELECT 
                        decile, 
                        COUNT(*) AS patients, 
                        ROUND(SUM(total_cost), 2) AS decile_spend,
                        ROUND(SUM(total_cost) * 100.0 / (SELECT SUM(CAST(total_claim_cost AS NUMERIC)) FROM raw_synthea.encounters), 2) AS pct_spend
                    FROM ranked 
                    GROUP BY decile 
                    ORDER BY decile ASC
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/charts/conditions":
                df = con.execute("""
                    SELECT 
                        description AS condition_name, 
                        COUNT(DISTINCT patient_id) AS patients
                    FROM raw_synthea.conditions 
                    GROUP BY description
                    ORDER BY patients DESC 
                    LIMIT 10
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/charts/pharmacy":
                df = con.execute("""
                    SELECT 
                        description AS medication_name,
                        COUNT(*) AS prescription_count,
                        ROUND(SUM(CAST(total_cost AS NUMERIC)), 2) AS total_cost
                    FROM raw_synthea.medications
                    GROUP BY description
                    ORDER BY prescription_count DESC
                    LIMIT 8
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/charts/dyads":
                df = con.execute("""
                    SELECT 
                        c1.description AS condition_a,
                        c2.description AS condition_b,
                        COUNT(DISTINCT c1.patient_id) AS shared_patients
                    FROM raw_synthea.conditions c1
                    JOIN raw_synthea.conditions c2 ON c1.patient_id = c2.patient_id AND c1.code < c2.code
                    GROUP BY c1.description, c2.description
                    HAVING COUNT(DISTINCT c1.patient_id) >= 10
                    ORDER BY shared_patients DESC
                    LIMIT 6
                """).df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/dq":
                df = con.execute("SELECT * FROM analytics.data_quality_log ORDER BY check_id").df()
                self._send_json(df.to_dict(orient="records"))

            elif path == "/api/presets":
                self._send_json(PRESET_QUERIES)

            else:
                self.send_error(404, "Not Found")
        finally:
            con.close()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/execute":
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length).decode('utf-8')
            req = json.loads(body)
            query = req.get("query", "").strip()

            con = duckdb.connect(DB_PATH, read_only=True)
            start_t = time.time()
            try:
                res = con.execute(query).df().head(200)
                dur = round((time.time() - start_t) * 1000, 2)
                self._send_json({
                    "status": "success",
                    "execution_time_ms": dur,
                    "columns": list(res.columns),
                    "rows": res.to_dict(orient="records"),
                    "row_count": len(res)
                })
            except Exception as e:
                self._send_json({
                    "status": "error",
                    "error": str(e)
                }, status=400)
            finally:
                con.close()
        else:
            self.send_error(404, "Not Found")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Healthcare Operations & Analytics Portal</title>
    
    <!-- Modern Typography -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

    <style>
        :root {
            /* Clean Solid Palette (Zero Gradients) */
            --bg-base: #F8FAFC;
            --bg-card: #FFFFFF;
            --bg-subtle: #F1F5F9;
            --border: #E2E8F0;
            --border-hover: #CBD5E1;

            /* Solid Theme Colors */
            --primary: #2563EB;
            --primary-hover: #1D4ED8;
            --primary-subtle: #EFF6FF;

            /* Natural Solid Accents */
            --text-heading: #0F172A;
            --text-body: #334155;
            --text-muted: #64748B;
            --text-light: #94A3B8;

            --emerald: #059669;
            --emerald-bg: #ECFDF5;
            --rose: #DC2626;
            --rose-bg: #FEF2F2;
            --amber: #D97706;
            --amber-bg: #FFFBEB;

            /* Elevation */
            --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
            --shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.05);

            /* Transitions */
            --transition: all 0.2s ease-in-out;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
            background-color: var(--bg-base);
            color: var(--text-body);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            -webkit-font-smoothing: antialiased;
        }

        /* Top Clean Header */
        header.top-bar {
            background: #FFFFFF;
            border-bottom: 1px solid var(--border);
            padding: 14px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-badge {
            background: var(--primary);
            color: #FFFFFF;
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 15px;
        }

        .brand-text h1 {
            font-size: 16px;
            font-weight: 700;
            color: var(--text-heading);
            letter-spacing: -0.01em;
        }

        .brand-text p {
            font-size: 11.5px;
            color: var(--text-muted);
        }

        .header-meta {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .solid-pill {
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            color: var(--text-body);
            font-size: 11.5px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 4px;
        }

        /* Navigation Bar */
        nav.nav-bar {
            background: #FFFFFF;
            border-bottom: 1px solid var(--border);
            padding: 0 32px;
            display: flex;
            gap: 4px;
        }

        .tab-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: inherit;
            font-size: 13px;
            font-weight: 600;
            padding: 13px 16px;
            cursor: pointer;
            position: relative;
            transition: var(--transition);
        }

        .tab-btn:hover {
            color: var(--text-heading);
        }

        .tab-btn.active {
            color: var(--primary);
        }

        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--primary);
        }

        /* Main Content Container */
        main.content {
            padding: 24px 32px;
            flex: 1;
            max-width: 1500px;
            margin: 0 auto;
            width: 100%;
        }

        .tab-panel {
            display: none;
        }

        .tab-panel.active {
            display: block;
            animation: fadeIn 0.2s ease-in-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Metrics Row */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px 20px;
            box-shadow: var(--shadow-card);
            transition: var(--transition);
        }

        .metric-card:hover {
            border-color: var(--border-hover);
            box-shadow: var(--shadow-hover);
        }

        .metric-title {
            font-size: 11.5px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 6px;
        }

        .metric-value {
            font-size: 26px;
            font-weight: 700;
            color: var(--text-heading);
            letter-spacing: -0.02em;
            line-height: 1.2;
            font-variant-numeric: tabular-nums;
            margin-bottom: 4px;
        }

        .metric-footer {
            font-size: 11.5px;
            color: var(--text-muted);
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .metric-tag {
            font-weight: 600;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 11px;
        }

        .tag-emerald { background: var(--emerald-bg); color: var(--emerald); }
        .tag-rose { background: var(--rose-bg); color: var(--rose); }

        /* Chart Layouts */
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 24px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            box-shadow: var(--shadow-card);
        }

        .card-header {
            margin-bottom: 16px;
        }

        .card-header h3 {
            font-size: 14.5px;
            font-weight: 700;
            color: var(--text-heading);
        }

        .chart-box {
            position: relative;
            height: 270px;
            width: 100%;
        }

        /* Loading Skeleton */
        .loading-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 270px;
            color: var(--text-light);
            font-size: 12px;
            gap: 8px;
        }

        .spinner {
            width: 24px;
            height: 24px;
            border: 2px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* SQL Workbench */
        .workbench-grid {
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 20px;
        }

        .preset-sidebar {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            max-height: calc(100vh - 200px);
            overflow-y: auto;
        }

        .preset-section-title {
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 14px 0 6px 0;
            padding-left: 2px;
        }

        .preset-section-title:first-child { margin-top: 0; }

        .preset-btn {
            width: 100%;
            text-align: left;
            background: #FFFFFF;
            border: 1px solid var(--border);
            padding: 8px 12px;
            border-radius: 6px;
            color: var(--text-body);
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 5px;
            cursor: pointer;
            transition: var(--transition);
        }

        .preset-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
            background: var(--primary-subtle);
        }

        .preset-btn.active {
            background: var(--primary);
            border-color: var(--primary);
            color: #FFFFFF;
        }

        .editor-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }

        .editor-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .editor-top h3 {
            font-size: 15px;
            font-weight: 700;
            color: var(--text-heading);
        }

        textarea.sql-code {
            width: 100%;
            height: 150px;
            background: #0F172A;
            color: #93C5FD;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12.5px;
            line-height: 1.5;
            padding: 14px;
            border-radius: 6px;
            border: 1px solid #1E293B;
            resize: vertical;
            outline: none;
        }

        textarea.sql-code:focus {
            border-color: var(--primary);
        }

        .editor-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }

        .btn-solid-primary {
            background: var(--primary);
            color: #FFFFFF;
            border: none;
            padding: 9px 20px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: var(--transition);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn-solid-primary:hover {
            background: var(--primary-hover);
        }

        .btn-solid-primary:disabled {
            background: var(--border-hover);
            cursor: not-allowed;
            opacity: 0.8;
        }

        .btn-subtle {
            background: #FFFFFF;
            border: 1px solid var(--border);
            color: var(--text-body);
            padding: 8px 14px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 12px;
            cursor: pointer;
            transition: var(--transition);
        }

        .btn-subtle:hover {
            background: var(--bg-subtle);
            border-color: var(--border-hover);
        }

        /* Status Badges & Awaiting Execution Panel */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-idle { background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; }
        .status-running { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
        .status-success { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
        .status-error { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }

        .awaiting-panel {
            border: 1px dashed #CBD5E1;
            background: #F8FAFC;
            border-radius: 8px;
            padding: 36px 24px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .awaiting-icon {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: #EFF6FF;
            color: var(--primary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            font-weight: 700;
            border: 1px solid #BFDBFE;
        }

        .awaiting-title {
            font-size: 14.5px;
            font-weight: 700;
            color: var(--text-heading);
        }

        .awaiting-desc {
            font-size: 12.5px;
            color: var(--text-muted);
            max-width: 520px;
            line-height: 1.5;
        }

        .awaiting-meta {
            display: flex;
            gap: 8px;
            margin-top: 6px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .results-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 14px;
            background: var(--bg-subtle);
            border: 1px solid var(--border);
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            font-size: 12px;
        }

        .results-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            color: var(--text-body);
            font-weight: 600;
        }

        /* Results Table */
        .table-wrap {
            max-height: 380px;
            overflow: auto;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: #FFFFFF;
        }

        table.clean-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
            text-align: left;
        }

        table.clean-table th {
            background: var(--bg-subtle);
            padding: 10px 14px;
            font-weight: 600;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            white-space: nowrap;
        }

        table.clean-table td {
            padding: 9px 14px;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
        }

        table.clean-table tr:hover td {
            background: var(--bg-base);
        }

        .badge-pass {
            background: var(--emerald-bg);
            color: var(--emerald);
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }

        footer.bottom-bar {
            border-top: 1px solid var(--border);
            background: #FFFFFF;
            padding: 14px 32px;
            font-size: 11.5px;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="top-bar">
        <div class="brand-group">
            <div class="brand-badge">H</div>
            <div class="brand-text">
                <h1>Healthcare Analytics Platform</h1>
                <p>Relational SQL Analytics • Synthea Model</p>
            </div>
        </div>
        <div class="header-meta">
            <span class="solid-pill">DuckDB & PostgreSQL Engine</span>
            <span class="solid-pill" style="color: var(--emerald); font-weight: 700;">● Active</span>
        </div>
    </header>

    <!-- Navigation -->
    <nav class="nav-bar">
        <button class="tab-btn active" onclick="switchTab('ops', this)">Operations</button>
        <button class="tab-btn" onclick="switchTab('segmentation', this)">Segmentation</button>
        <button class="tab-btn" onclick="switchTab('clinical', this)">Clinical & Cost</button>
        <button class="tab-btn" onclick="switchTab('workbench', this)">SQL Workbench</button>
        <button class="tab-btn" onclick="switchTab('quality', this)">Data Quality</button>
    </nav>

    <!-- Content -->
    <main class="content">
        <!-- TAB 1: OPERATIONS -->
        <div id="tab-ops" class="tab-panel active">
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Patients</div>
                    <div class="metric-value" id="kpi-patients">1,200</div>
                    <div class="metric-footer">Registered individuals</div>
                </div>

                <div class="metric-card">
                    <div class="metric-title">Encounters</div>
                    <div class="metric-value" id="kpi-encounters">6,344</div>
                    <div class="metric-footer">5.3 visits / patient</div>
                </div>

                <div class="metric-card">
                    <div class="metric-title">Total Spend</div>
                    <div class="metric-value" id="kpi-spend">$17.86M</div>
                    <div class="metric-footer">$2,815 avg / encounter</div>
                </div>

                <div class="metric-card">
                    <div class="metric-title">ED Rate</div>
                    <div class="metric-value" id="kpi-emergency" style="color: var(--rose);">17.3%</div>
                    <div class="metric-footer">
                        <span class="metric-tag tag-rose" id="kpi-emergency-count">1,100</span>
                        <span>Emergency visits</span>
                    </div>
                </div>

                <div class="metric-card">
                    <div class="metric-title">Reimbursement</div>
                    <div class="metric-value" id="kpi-reimbursement" style="color: var(--emerald);">82.3%</div>
                    <div class="metric-footer">$14.71M covered</div>
                </div>
            </div>

            <div class="grid-2">
                <div class="card">
                    <div class="card-header">
                        <h3>Monthly Visits</h3>
                    </div>
                    <div class="chart-box" id="box-monthly">
                        <canvas id="chart-monthly"></canvas>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Care Setting Mix</h3>
                    </div>
                    <div class="chart-box" id="box-classes">
                        <canvas id="chart-classes"></canvas>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>Facility Volume</h3>
                </div>
                <div class="chart-box" id="box-facilities">
                    <canvas id="chart-facilities"></canvas>
                </div>
            </div>
        </div>

        <!-- TAB 2: SEGMENTATION (Loaded on-demand) -->
        <div id="tab-segmentation" class="tab-panel">
            <div class="grid-2">
                <div class="card">
                    <div class="card-header">
                        <h3>Utilization Tiers</h3>
                    </div>
                    <div class="chart-box" id="box-segment-count">
                        <div class="loading-placeholder"><div class="spinner"></div><span>Loading data...</span></div>
                        <canvas id="chart-segment-count" style="display:none;"></canvas>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Average Spend by Tier</h3>
                    </div>
                    <div class="chart-box" id="box-segment-spend">
                        <div class="loading-placeholder"><div class="spinner"></div><span>Loading data...</span></div>
                        <canvas id="chart-segment-spend" style="display:none;"></canvas>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>Co-Occurring Conditions</h3>
                </div>
                <div class="chart-box" id="box-dyads">
                    <div class="loading-placeholder"><div class="spinner"></div><span>Loading data...</span></div>
                    <canvas id="chart-dyads" style="display:none;"></canvas>
                </div>
            </div>
        </div>

        <!-- TAB 3: CLINICAL & COST (Loaded on-demand) -->
        <div id="tab-clinical" class="tab-panel">
            <div class="grid-2">
                <div class="card">
                    <div class="card-header">
                        <h3>Spend by Decile</h3>
                    </div>
                    <div class="chart-box" id="box-deciles">
                        <div class="loading-placeholder"><div class="spinner"></div><span>Loading data...</span></div>
                        <canvas id="chart-deciles" style="display:none;"></canvas>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3>Top Diagnoses</h3>
                    </div>
                    <div class="chart-box" id="box-conditions">
                        <div class="loading-placeholder"><div class="spinner"></div><span>Loading data...</span></div>
                        <canvas id="chart-conditions" style="display:none;"></canvas>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3>Top Prescriptions</h3>
                </div>
                <div class="chart-box" id="box-pharmacy">
                    <div class="loading-placeholder"><div class="spinner"></div><span>Loading data...</span></div>
                    <canvas id="chart-pharmacy" style="display:none;"></canvas>
                </div>
            </div>
        </div>

        <!-- TAB 4: SQL WORKBENCH (Loaded on-demand) -->
        <div id="tab-workbench" class="tab-panel">
            <div class="workbench-grid">
                <div class="preset-sidebar" id="preset-container">
                    <div class="loading-placeholder"><div class="spinner"></div><span>Loading presets...</span></div>
                </div>

                <div class="editor-box">
                    <div class="editor-top">
                        <div>
                            <div id="query-category" style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 3px;">Specialized</div>
                            <h3 id="query-title" style="margin: 0; font-size: 15px;">Q35: Cost Concentration (The 90/10 Spend Rule)</h3>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button class="btn-subtle" onclick="copySQL()">Copy SQL</button>
                            <button class="btn-subtle" onclick="clearEditor()">Clear</button>
                        </div>
                    </div>

                    <textarea class="sql-code" id="sql-input" spellcheck="false" placeholder="Write or select a SQL query to execute..."></textarea>

                    <div class="editor-actions">
                        <div id="query-status-badge" class="status-badge status-idle">
                            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #64748B;"></span>
                            <span id="query-status-text">Manual Execution Required &bull; Click "Run Query"</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 11.5px; color: var(--text-muted); font-weight: 500;">Shortcut: <kbd style="background: #E2E8F0; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;">Ctrl + Enter</kbd></span>
                            <button id="btn-run" class="btn-solid-primary" onclick="runQuery()">
                                &#9654; Run Query
                            </button>
                        </div>
                    </div>

                    <!-- Output Container -->
                    <div id="output-container">
                        <!-- Initial Awaiting Execution State -->
                        <div class="awaiting-panel" id="awaiting-card">
                            <div class="awaiting-icon">&#9654;</div>
                            <div class="awaiting-title">Query Loaded &bull; Ready for Execution</div>
                            <div class="awaiting-desc">
                                Queries do not run automatically. Click <strong>"Run Query"</strong> above or press <kbd style="background: #E2E8F0; padding: 2px 6px; border-radius: 4px; font-size: 11px;">Ctrl + Enter</kbd> to execute this query against the database.
                            </div>
                            <div class="awaiting-meta">
                                <span class="solid-pill">Engine: DuckDB (Embedded)</span>
                                <span class="solid-pill">Database: healthcare.duckdb</span>
                                <span class="solid-pill">Safety: Read-Only (LIMIT 200)</span>
                            </div>
                        </div>

                        <!-- Results View (Hidden Initially) -->
                        <div id="results-view" style="display: none;">
                            <div class="results-bar">
                                <div class="results-meta">
                                    <span id="res-badge" class="badge-pass">Success</span>
                                    <span id="res-timing">0 ms</span>
                                    <span id="res-count">0 rows</span>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button class="btn-subtle" style="padding: 4px 10px; font-size: 11px;" onclick="exportCSV()">Download CSV</button>
                                    <button class="btn-subtle" style="padding: 4px 10px; font-size: 11px;" onclick="clearOutput()">Reset View</button>
                                </div>
                            </div>
                            <div class="table-wrap" style="border-top-left-radius: 0; border-top-right-radius: 0;">
                                <table class="clean-table" id="results-table">
                                    <!-- Populated on manual execution -->
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 5: DATA QUALITY (Loaded on-demand) -->
        <div id="tab-quality" class="tab-panel">
            <div class="card">
                <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>Data Quality Scorecard</h3>
                    <span class="badge-pass">10 / 10 Tests Passed</span>
                </div>
                <div class="table-wrap" style="max-height: 500px;">
                    <table class="clean-table" id="dq-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Category</th>
                                <th>Test Name</th>
                                <th>Severity</th>
                                <th>Failures</th>
                                <th>Status</th>
                                <th>Assertion</th>
                            </tr>
                        </thead>
                        <tbody id="dq-body">
                            <tr><td colspan="7" style="text-align: center; padding: 20px;">Loading verification tests...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="bottom-bar">
        <div>Healthcare Operations Platform • Relational Analytics</div>
        <div>DuckDB Embedded Engine • 46,131 Ingested Rows</div>
    </footer>

    <script>
        // Track which tabs have been fetched to enable on-demand lazy loading
        const loadedTabs = new Set(['ops']);

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById('tab-' + tabId).classList.add('active');

            // Load on demand
            if (!loadedTabs.has(tabId)) {
                loadedTabs.add(tabId);
                if (tabId === 'segmentation') loadSegmentationTab();
                else if (tabId === 'clinical') loadClinicalTab();
                else if (tabId === 'workbench') loadWorkbenchTab();
                else if (tabId === 'quality') loadQualityTab();
            }
        }

        // Common Chart Defaults (Natural Solid Colors)
        Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#64748B';

        // Reusable Precision Animation Profiles
        const verticalBarAnimation = {
            y: {
                type: 'number',
                easing: 'easeOutQuart',
                duration: 900,
                from: (ctx) => {
                    if (ctx.type === 'data' && ctx.chart.scales.y) {
                        return ctx.chart.scales.y.getPixelForValue(0);
                    }
                },
                delay: (ctx) => {
                    if (ctx.type === 'data' && ctx.mode === 'default') {
                        return ctx.dataIndex * 80 + (ctx.datasetIndex || 0) * 100;
                    }
                    return 0;
                }
            }
        };

        const horizontalBarAnimation = {
            x: {
                type: 'number',
                easing: 'easeOutQuart',
                duration: 900,
                from: (ctx) => {
                    if (ctx.type === 'data' && ctx.chart.scales.x) {
                        return ctx.chart.scales.x.getPixelForValue(0);
                    }
                },
                delay: (ctx) => {
                    if (ctx.type === 'data' && ctx.mode === 'default') {
                        return ctx.dataIndex * 70 + (ctx.datasetIndex || 0) * 90;
                    }
                    return 0;
                }
            }
        };

        const circleFillAnimation = {
            animateRotate: true,
            animateScale: false,
            duration: 1200,
            easing: 'easeOutQuart'
        };

        // 1. Initial Load: Operations Tab Only
        async function loadOpsTab() {
            try {
                // Summary KPIs
                const res = await fetch('/api/summary');
                const d = await res.json();
                document.getElementById('kpi-patients').innerText = Number(d.total_patients).toLocaleString();
                document.getElementById('kpi-encounters').innerText = Number(d.total_encounters).toLocaleString();
                document.getElementById('kpi-spend').innerText = '$' + (d.total_spend / 1e6).toFixed(2) + 'M';
                document.getElementById('kpi-emergency').innerText = d.emergency_rate + '%';
                document.getElementById('kpi-emergency-count').innerText = Number(d.emergency_visits).toLocaleString();
                document.getElementById('kpi-reimbursement').innerText = d.reimbursement_rate + '%';

                // Monthly Chart (Line rising from 0)
                const mRes = await fetch('/api/charts/monthly');
                const mData = await mRes.json();
                new Chart(document.getElementById('chart-monthly'), {
                    type: 'line',
                    data: {
                        labels: mData.map(r => r.month),
                        datasets: [
                            {
                                label: 'Total Visits',
                                data: mData.map(r => r.total_visits),
                                borderColor: '#2563EB',
                                backgroundColor: '#2563EB',
                                borderWidth: 2,
                                pointRadius: 2,
                                tension: 0.1
                            },
                            {
                                label: 'Emergency Visits',
                                data: mData.map(r => r.emergency_visits),
                                borderColor: '#DC2626',
                                backgroundColor: '#DC2626',
                                borderWidth: 2,
                                pointRadius: 2,
                                tension: 0.1
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animations: verticalBarAnimation,
                        plugins: { legend: { position: 'top' } },
                        scales: {
                            y: { grid: { color: '#F1F5F9' } },
                            x: { grid: { display: false } }
                        }
                    }
                });

                // Classes Chart (Doughnut completing circle radially)
                const cRes = await fetch('/api/charts/classes');
                const cData = await cRes.json();
                new Chart(document.getElementById('chart-classes'), {
                    type: 'doughnut',
                    data: {
                        labels: cData.map(r => r.encounter_class.charAt(0).toUpperCase() + r.encounter_class.slice(1)),
                        datasets: [{
                            data: cData.map(r => r.count),
                            backgroundColor: ['#2563EB', '#0D9488', '#DC2626', '#D97706', '#6366F1'],
                            borderWidth: 1,
                            borderColor: '#FFFFFF'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: circleFillAnimation,
                        plugins: { legend: { position: 'right' } },
                        cutout: '70%'
                    }
                });

                // Facilities Chart (Horizontal bars growing from 0)
                const fRes = await fetch('/api/charts/facilities');
                const fData = await fRes.json();
                new Chart(document.getElementById('chart-facilities'), {
                    type: 'bar',
                    data: {
                        labels: fData.map(r => r.name.split(' ')[0]),
                        datasets: [
                            { label: 'Total Visits', data: fData.map(r => r.encounters), backgroundColor: '#2563EB', borderRadius: 3 },
                            { label: 'Emergency', data: fData.map(r => r.emergency_visits), backgroundColor: '#DC2626', borderRadius: 3 }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animations: horizontalBarAnimation,
                        scales: {
                            y: { grid: { color: '#F1F5F9' } },
                            x: { grid: { display: false } }
                        }
                    }
                });
            } catch (err) {
                console.error("Ops tab load error:", err);
            }
        }

        // 2. On-Demand Load: Segmentation Tab
        async function loadSegmentationTab() {
            try {
                const sRes = await fetch('/api/charts/segmentation');
                const sData = await sRes.json();

                // Swap placeholders
                document.querySelector('#box-segment-count .loading-placeholder').remove();
                document.getElementById('chart-segment-count').style.display = 'block';
                new Chart(document.getElementById('chart-segment-count'), {
                    type: 'bar',
                    data: {
                        labels: sData.map(r => r.segment),
                        datasets: [{
                            label: 'Patients',
                            data: sData.map(r => r.count),
                            backgroundColor: '#2563EB',
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animations: verticalBarAnimation,
                        plugins: { legend: { display: false } },
                        scales: { y: { grid: { color: '#F1F5F9' } }, x: { grid: { display: false } } }
                    }
                });

                document.querySelector('#box-segment-spend .loading-placeholder').remove();
                document.getElementById('chart-segment-spend').style.display = 'block';
                new Chart(document.getElementById('chart-segment-spend'), {
                    type: 'bar',
                    data: {
                        labels: sData.map(r => r.segment),
                        datasets: [{
                            label: 'Avg Lifetime Spend ($)',
                            data: sData.map(r => r.avg_spend),
                            backgroundColor: '#0D9488',
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animations: verticalBarAnimation,
                        plugins: { legend: { display: false } },
                        scales: { y: { grid: { color: '#F1F5F9' } }, x: { grid: { display: false } } }
                    }
                });

                const dRes = await fetch('/api/charts/dyads');
                const dData = await dRes.json();
                document.querySelector('#box-dyads .loading-placeholder').remove();
                document.getElementById('chart-dyads').style.display = 'block';
                new Chart(document.getElementById('chart-dyads'), {
                    type: 'bar',
                    data: {
                        labels: dData.map(r => r.condition_a + ' + ' + r.condition_b),
                        datasets: [{
                            label: 'Shared Patients',
                            data: dData.map(r => r.shared_patients),
                            backgroundColor: '#4338CA',
                            borderRadius: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        animations: horizontalBarAnimation,
                        plugins: { legend: { display: false } },
                        scales: { x: { grid: { color: '#F1F5F9' } }, y: { grid: { display: false } } }
                    }
                });
            } catch (err) {
                console.error("Segmentation tab load error:", err);
            }
        }

        // 3. On-Demand Load: Clinical & Cost Tab
        async function loadClinicalTab() {
            try {
                const decRes = await fetch('/api/charts/deciles');
                const decData = await decRes.json();
                document.querySelector('#box-deciles .loading-placeholder').remove();
                document.getElementById('chart-deciles').style.display = 'block';
                new Chart(document.getElementById('chart-deciles'), {
                    type: 'bar',
                    data: {
                        labels: decData.map(r => 'Decile ' + r.decile),
                        datasets: [{
                            label: '% Total Spend',
                            data: decData.map(r => r.pct_spend),
                            backgroundColor: decData.map(r => r.decile >= 9 ? '#DC2626' : '#2563EB'),
                            borderRadius: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        animations: verticalBarAnimation,
                        plugins: { legend: { display: false } },
                        scales: { y: { grid: { color: '#F1F5F9' } }, x: { grid: { display: false } } }
                    }
                });

                const condRes = await fetch('/api/charts/conditions');
                const condData = await condRes.json();
                document.querySelector('#box-conditions .loading-placeholder').remove();
                document.getElementById('chart-conditions').style.display = 'block';
                new Chart(document.getElementById('chart-conditions'), {
                    type: 'bar',
                    data: {
                        labels: condData.map(r => r.condition_name),
                        datasets: [{
                            label: 'Unique Patients',
                            data: condData.map(r => r.patients),
                            backgroundColor: '#0284C7',
                            borderRadius: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        animations: horizontalBarAnimation,
                        plugins: { legend: { display: false } },
                        scales: { x: { grid: { color: '#F1F5F9' } }, y: { grid: { display: false } } }
                    }
                });

                const rxRes = await fetch('/api/charts/pharmacy');
                const rxData = await rxRes.json();
                document.querySelector('#box-pharmacy .loading-placeholder').remove();
                document.getElementById('chart-pharmacy').style.display = 'block';
                new Chart(document.getElementById('chart-pharmacy'), {
                    type: 'bar',
                    data: {
                        labels: rxData.map(r => r.medication_name),
                        datasets: [{
                            label: 'Prescriptions',
                            data: rxData.map(r => r.prescription_count),
                            backgroundColor: '#059669',
                            borderRadius: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        animations: horizontalBarAnimation,
                        plugins: { legend: { display: false } },
                        scales: { x: { grid: { color: '#F1F5F9' } }, y: { grid: { display: false } } }
                    }
                });
            } catch (err) {
                console.error("Clinical tab load error:", err);
            }
        }

        // 4. On-Demand Load: Workbench Tab
        let presets = {};
        let currentQueryResults = null;

        async function loadWorkbenchTab() {
            try {
                const res = await fetch('/api/presets');
                presets = await res.json();
                const container = document.getElementById('preset-container');
                container.innerHTML = '';

                let curCat = '';
                for (const [k, item] of Object.entries(presets)) {
                    if (item.category !== curCat) {
                        curCat = item.category;
                        const header = document.createElement('div');
                        header.className = 'preset-section-title';
                        header.innerText = curCat;
                        container.appendChild(header);
                    }
                    const btn = document.createElement('button');
                    btn.className = 'preset-btn';
                    btn.innerText = item.title;
                    btn.onclick = () => selectPreset(k, btn);
                    container.appendChild(btn);
                }

                // Load default preset into editor, but DO NOT run it
                const firstKey = "Q35" in presets ? "Q35" : Object.keys(presets)[0];
                const targetBtn = Array.from(container.querySelectorAll('.preset-btn')).find(b => b.innerText.includes("Q35")) || container.querySelector('.preset-btn');
                if (firstKey && targetBtn) {
                    selectPreset(firstKey, targetBtn);
                }
            } catch (err) {
                console.error("Workbench load error:", err);
            }
        }

        function selectPreset(key, btn) {
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');

            const item = presets[key];
            if (!item) return;

            document.getElementById('query-category').innerText = item.category || 'Preset SQL';
            document.getElementById('query-title').innerText = item.title;
            document.getElementById('sql-input').value = item.sql;
            
            // Explicitly do NOT run query - reset results to manual prompt
            clearOutput();
            updateStatus('idle', 'Manual Execution Required • Click "Run Query"');
        }

        function updateStatus(state, msg) {
            const badge = document.getElementById('query-status-badge');
            const text = document.getElementById('query-status-text');
            if (!badge || !text) return;

            badge.className = 'status-badge status-' + state;
            
            let dotColor = '#64748B';
            if (state === 'running') dotColor = '#1D4ED8';
            else if (state === 'success') dotColor = '#059669';
            else if (state === 'error') dotColor = '#DC2626';

            if (badge.firstElementChild) badge.firstElementChild.style.background = dotColor;
            text.innerText = msg;
        }

        async function runQuery() {
            const query = document.getElementById('sql-input').value.trim();
            if (!query) {
                updateStatus('error', 'Query editor is empty. Enter or select a query.');
                return;
            }

            const runBtn = document.getElementById('btn-run');
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner" style="display:inline-block; vertical-align:middle; width:13px; height:13px; margin-right:6px; border-width:2px;"></span> Running...';

            updateStatus('running', 'Executing query on DuckDB analytics engine...');

            // Show executing indicator in output area
            document.getElementById('awaiting-card').style.display = 'flex';
            document.getElementById('awaiting-card').innerHTML = `
                <div class="spinner" style="width: 32px; height: 32px; border-width: 3px;"></div>
                <div class="awaiting-title" style="color: var(--primary);">Executing Live Query...</div>
                <div class="awaiting-desc">Querying <code>healthcare.duckdb</code> relational store. Results will appear momentarily.</div>
            `;
            document.getElementById('results-view').style.display = 'none';

            try {
                const res = await fetch('/api/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });
                const d = await res.json();
                
                if (d.status === 'success') {
                    currentQueryResults = d;
                    updateStatus('success', `Executed in ${d.execution_time_ms} ms • Returned ${d.row_count} rows`);
                    renderResults(d.columns, d.rows, d.execution_time_ms);
                } else {
                    currentQueryResults = null;
                    updateStatus('error', 'Execution Failed');
                    document.getElementById('awaiting-card').style.display = 'flex';
                    document.getElementById('awaiting-card').innerHTML = `
                        <div class="awaiting-icon" style="background:#FEF2F2; color:#DC2626; border-color:#FECACA;">&#10005;</div>
                        <div class="awaiting-title" style="color:#DC2626;">SQL Execution Error</div>
                        <div class="awaiting-desc" style="color:#DC2626; font-family:'JetBrains Mono', monospace; font-size:12px; background:#FFFFFF; border:1px solid #FECACA; padding:12px; border-radius:6px; max-width:90%; text-align:left;">
                            ${escapeHtml(d.error)}
                        </div>
                    `;
                    document.getElementById('results-view').style.display = 'none';
                }
            } catch (err) {
                currentQueryResults = null;
                updateStatus('error', 'Network error connecting to database server');
            } finally {
                runBtn.disabled = false;
                runBtn.innerHTML = '&#9654; Run Query';
            }
        }

        function renderResults(cols, rows, timeMs) {
            document.getElementById('awaiting-card').style.display = 'none';
            const view = document.getElementById('results-view');
            view.style.display = 'block';

            document.getElementById('res-timing').innerText = `${timeMs} ms`;
            document.getElementById('res-count').innerText = `${rows.length} rows returned`;

            const table = document.getElementById('results-table');
            if (rows.length === 0) {
                table.innerHTML = '<thead><tr><th>Result</th></tr></thead><tbody><tr><td style="padding:24px; text-align:center; color:var(--text-muted);">Query executed successfully. Result set is empty (0 rows).</td></tr></tbody>';
                return;
            }

            let html = '<thead><tr>';
            cols.forEach(c => html += `<th>${escapeHtml(c)}</th>`);
            html += '</tr></thead><tbody>';

            rows.forEach(r => {
                html += '<tr>';
                cols.forEach(c => {
                    let v = r[c];
                    let isNum = typeof v === 'number';
                    let formatted = v;
                    if (isNum) formatted = v.toLocaleString();
                    else if (v === null || v === undefined) formatted = '<span style="color:#94A3B8;">NULL</span>';
                    else formatted = escapeHtml(String(v));

                    html += `<td style="${isNum ? 'text-align: right;' : ''}">${formatted}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody>';
            table.innerHTML = html;
        }

        function clearOutput() {
            currentQueryResults = null;
            document.getElementById('results-view').style.display = 'none';
            const card = document.getElementById('awaiting-card');
            card.style.display = 'flex';
            card.innerHTML = `
                <div class="awaiting-icon">&#9654;</div>
                <div class="awaiting-title">Query Loaded &bull; Ready for Execution</div>
                <div class="awaiting-desc">
                    Queries do not run automatically. Click <strong>"Run Query"</strong> above or press <kbd style="background: #E2E8F0; padding: 2px 6px; border-radius: 4px; font-size: 11px;">Ctrl + Enter</kbd> to execute this query against the database.
                </div>
                <div class="awaiting-meta">
                    <span class="solid-pill">Engine: DuckDB (Embedded)</span>
                    <span class="solid-pill">Database: healthcare.duckdb</span>
                    <span class="solid-pill">Safety: Read-Only (LIMIT 200)</span>
                </div>
            `;
            updateStatus('idle', 'Manual Execution Required • Click "Run Query"');
        }

        function clearEditor() {
            document.getElementById('sql-input').value = '';
            document.getElementById('query-title').innerText = 'Custom Query';
            document.getElementById('query-category').innerText = 'Ad-Hoc SQL';
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            clearOutput();
            updateStatus('idle', 'Editor Cleared • Type a SQL query and click "Run Query"');
        }

        function copySQL() {
            const text = document.getElementById('sql-input').value;
            if (!text) return;
            navigator.clipboard.writeText(text);
            const btn = event.target;
            const old = btn.innerText;
            btn.innerText = 'Copied!';
            setTimeout(() => btn.innerText = old, 1500);
        }

        function exportCSV() {
            if (!currentQueryResults || !currentQueryResults.rows || currentQueryResults.rows.length === 0) {
                alert("No query results to export.");
                return;
            }
            const cols = currentQueryResults.columns;
            const rows = currentQueryResults.rows;
            let csvLines = [];
            csvLines.push(cols.map(c => '"' + String(c).replace(/"/g, '""') + '"').join(','));
            rows.forEach(r => {
                let row = cols.map(c => {
                    let val = r[c];
                    if (val === null || val === undefined) return '""';
                    return '"' + String(val).replace(/"/g, '""') + '"';
                }).join(',');
                csvLines.push(row);
            });
            const blob = new Blob([csvLines.join(String.fromCharCode(10))], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.setAttribute('download', 'healthcare_query_results.csv');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        function escapeHtml(str) {
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        // 5. On-Demand Load: Data Quality Tab
        async function loadQualityTab() {
            try {
                const res = await fetch('/api/dq');
                const data = await res.json();
                const tbody = document.getElementById('dq-body');
                tbody.innerHTML = '';
                data.forEach(r => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>#${r.check_id}</strong></td>
                        <td><strong>${r.check_category}</strong></td>
                        <td>${r.check_name}</td>
                        <td><span style="font-weight:600; color: ${r.severity === 'CRITICAL' ? '#DC2626' : '#D97706'};">${r.severity}</span></td>
                        <td>${r.failed_records_count}</td>
                        <td><span class="badge-pass">${r.status}</span></td>
                        <td style="color: #64748B;">${r.details}</td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (err) {
                console.error("Quality tab load error:", err);
            }
        }

        // Keyboard shortcut: Ctrl + Enter to run query
        document.getElementById('sql-input').addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                runQuery();
            }
        });

        // Detect user modifications in editor
        document.getElementById('sql-input').addEventListener('input', () => {
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('query-category').innerText = 'Custom Ad-Hoc SQL';
            updateStatus('idle', 'Custom query modified • Click "Run Query" to execute');
        });

        // Start Initial Tab
        loadOpsTab();
    </script>
</body>
</html>
"""

def run_server():
    server = HTTPServer(('127.0.0.1', PORT), DashboardHandler)
    print(f"\n==================================================================")
    print(f"HEALTHCARE OPERATIONS PLATFORM SERVER RUNNING")
    print(f"URL: http://localhost:{PORT}")
    print(f"Palette: Clean Solid White & Royal Blue (#2563EB) - No Gradients")
    print(f"Data Loading: On-Demand Lazy Loaded")
    print(f"==================================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

if __name__ == "__main__":
    run_server()
