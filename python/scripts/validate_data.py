"""
Automated Data Quality & Validation Runner
Executes sql/01_data_quality.sql and produces reports/data_quality_report.csv
Project: Healthcare Operations & Patient Analytics
"""
import os
import csv
import duckdb

def run_data_validation(db_path="healthcare.duckdb", output_csv="reports/data_quality_report.csv"):
    print("\n==================================================")
    print("Executing Automated Data Quality Validation Suite")
    print("==================================================")
    
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    con = duckdb.connect(db_path)
    
    # Create analytics.data_quality_log table
    con.execute("""
        CREATE SCHEMA IF NOT EXISTS analytics;
        DROP TABLE IF EXISTS analytics.data_quality_log;
        CREATE TABLE analytics.data_quality_log (
            check_id INTEGER,
            check_category VARCHAR,
            check_name VARCHAR,
            severity VARCHAR,
            failed_records_count BIGINT,
            status VARCHAR,
            details VARCHAR
        );
    """)

    test_queries = [
        # 1. Uniqueness - Duplicate Patients
        (1, "Uniqueness", "Duplicate Patient IDs", "CRITICAL", """
            SELECT COUNT(*) FROM (
                SELECT patient_id, COUNT(*) 
                FROM raw_synthea.patients 
                GROUP BY patient_id 
                HAVING COUNT(*) > 1
            ) sub;
        """, "Repeated patient_id records detected in patients table"),

        # 2. Uniqueness - Duplicate Encounters
        (2, "Uniqueness", "Duplicate Encounter IDs", "CRITICAL", """
            SELECT COUNT(*) FROM (
                SELECT encounter_id, COUNT(*) 
                FROM raw_synthea.encounters 
                GROUP BY encounter_id 
                HAVING COUNT(*) > 1
            ) sub;
        """, "Repeated encounter_id records detected in encounters table"),

        # 3. Completeness - Null Primary Keys
        (3, "Completeness", "Null Encounter PK or Start Time", "CRITICAL", """
            SELECT COUNT(*) FROM raw_synthea.encounters
            WHERE encounter_id IS NULL OR start_time IS NULL;
        """, "Encounters missing primary key or start timestamp"),

        # 4. Temporal Validity - Stop < Start
        (4, "Temporal Validity", "Encounter End Prior to Start", "CRITICAL", """
            SELECT COUNT(*) FROM raw_synthea.encounters
            WHERE stop_time IS NOT NULL AND stop_time < start_time;
        """, "Encounters where stop_time < start_time"),

        # 5. Temporal Validity - Condition End < Start
        (5, "Temporal Validity", "Condition End Prior to Start", "HIGH", """
            SELECT COUNT(*) FROM raw_synthea.conditions
            WHERE end_date IS NOT NULL AND end_date < start_date;
        """, "Conditions where end_date < start_date"),

        # 6. Financial Validity - Negative Costs
        (6, "Financial Validity", "Negative Encounter Costs", "HIGH", """
            SELECT COUNT(*) FROM raw_synthea.encounters
            WHERE base_encounter_cost < 0 OR total_claim_cost < 0 OR payer_coverage < 0;
        """, "Encounters with negative financial values"),

        # 7. Financial Validity - Coverage > Claim
        (7, "Financial Validity", "Payer Coverage Exceeds Claim Cost", "MEDIUM", """
            SELECT COUNT(*) FROM raw_synthea.encounters
            WHERE payer_coverage > total_claim_cost + 0.01;
        """, "Payer coverage exceeding total claim amount"),

        # 8. Referential Integrity - Orphan Encounters
        (8, "Referential Integrity", "Orphan Encounters (Invalid Patient)", "CRITICAL", """
            SELECT COUNT(*) FROM raw_synthea.encounters e
            LEFT JOIN raw_synthea.patients p ON e.patient_id = p.patient_id
            WHERE p.patient_id IS NULL;
        """, "Encounters pointing to missing patient_id"),

        # 9. Referential Integrity - Orphan Conditions
        (9, "Referential Integrity", "Orphan Conditions (Invalid Encounter)", "CRITICAL", """
            SELECT COUNT(*) FROM raw_synthea.conditions c
            LEFT JOIN raw_synthea.encounters e ON c.encounter_id = e.encounter_id
            WHERE e.encounter_id IS NULL;
        """, "Conditions pointing to missing encounter_id"),

        # 10. Referential Integrity - Orphan Medications
        (10, "Referential Integrity", "Orphan Medications (Invalid Patient)", "CRITICAL", """
            SELECT COUNT(*) FROM raw_synthea.medications m
            LEFT JOIN raw_synthea.patients p ON m.patient_id = p.patient_id
            WHERE p.patient_id IS NULL;
        """, "Medications pointing to missing patient_id")
    ]

    results = []
    has_critical_failure = False

    for c_id, category, name, severity, query, details in test_queries:
        fail_count = con.execute(query).fetchone()[0]
        status = "PASSED" if fail_count == 0 else "FAILED"
        if status == "FAILED" and severity == "CRITICAL":
            has_critical_failure = True
            
        con.execute("""
            INSERT INTO analytics.data_quality_log VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (c_id, category, name, severity, fail_count, status, details))

        results.append({
            "check_id": c_id,
            "category": category,
            "name": name,
            "severity": severity,
            "failed_records": fail_count,
            "status": status,
            "details": details
        })
        print(f"[{status}] Check #{c_id:02d}: {name} (Severity: {severity}, Failures: {fail_count:,})")

    # Export to reports/data_quality_report.csv
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check_id", "category", "name", "severity", "failed_records", "status", "details"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[OK] Exported scorecard to: {output_csv}")
    con.close()

    if has_critical_failure:
        print("\n[FAIL] DATA QUALITY GATE FAILED: Critical errors detected. Downstream analytics halted.")
        return False
    else:
        print("\n[PASS] DATA QUALITY GATE PASSED: Zero critical failures detected. Safe for analytics.")
        return True

if __name__ == "__main__":
    run_data_validation()
