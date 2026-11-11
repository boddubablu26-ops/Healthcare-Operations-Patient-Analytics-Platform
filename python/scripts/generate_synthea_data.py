"""
High-Fidelity Synthea Synthetic Healthcare Data Generator
Generates realistic multi-table relational healthcare data conforming to the official Synthea™ schema.
Tables: patients, encounters, conditions, medications, procedures, observations, organizations, providers, payers
"""
import os
import uuid
import random
from datetime import datetime, timedelta, date
import csv

def generate_dataset(output_dir="data/raw", num_patients=1200, seed=42):
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    print(f"Generating realistic Synthea synthetic dataset ({num_patients} patients)...")

    # 1. Organizations
    org_names = [
        ("Mass General Brigham", "55 Fruit St", "Boston", "MA", "02114", "617-726-2000", 250000000.00, 950),
        ("Beth Israel Deaconess Medical Center", "330 Brookline Ave", "Boston", "MA", "02215", "617-667-7000", 180000000.00, 700),
        ("Boston Medical Center", "1 Boston Med Ctr Pl", "Boston", "MA", "02118", "617-638-8000", 140000000.00, 550),
        ("Cambridge Health Alliance", "1493 Cambridge St", "Cambridge", "MA", "02139", "617-665-1000", 95000000.00, 320),
        ("UMass Memorial Medical Center", "55 Lake Ave N", "Worcester", "MA", "01655", "508-334-1000", 160000000.00, 620),
        ("Baystate Medical Center", "759 Chestnut St", "Springfield", "MA", "01199", "413-794-0000", 120000000.00, 480),
        ("South Shore Hospital", "55 Fogg Rd", "South Weymouth", "MA", "02190", "781-624-8000", 85000000.00, 350),
        ("Lahey Hospital & Medical Center", "41 Mall Rd", "Burlington", "MA", "01805", "781-744-5100", 110000000.00, 420),
    ]
    organizations = []
    for name, addr, city, state, zip_c, phone, rev, util in org_names:
        organizations.append({
            "organization_id": str(uuid.uuid4()),
            "name": name,
            "address": addr,
            "city": city,
            "state": state,
            "zip": zip_c,
            "phone": phone,
            "revenue": f"{rev:.2f}",
            "utilization": util
        })
    with open(os.path.join(output_dir, "organizations.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(organizations[0].keys()))
        writer.writeheader()
        writer.writerows(organizations)
    print("[OK] Saved organizations.csv")

    # 2. Payers
    payer_defs = [
        ("Medicare", "Government", "7500 Security Blvd", "Baltimore", "MD", "21244", "800-633-4227", 90000000.00, 5000000.00, 95000000.00),
        ("Medicaid", "Government", "600 Washington St", "Boston", "MA", "02111", "800-841-2900", 65000000.00, 3000000.00, 68000000.00),
        ("Blue Cross Blue Shield of MA", "Private", "101 Huntington Ave", "Boston", "MA", "02199", "800-262-2583", 110000000.00, 8000000.00, 118000000.00),
        ("Harvard Pilgrim Health Care", "Private", "93 Worcester St", "Wellesley", "MA", "02481", "888-333-4742", 75000000.00, 6000000.00, 81000000.00),
        ("Tufts Health Plan", "Private", "705 Mt Auburn St", "Watertown", "MA", "02472", "800-462-0224", 55000000.00, 4500000.00, 59500000.00),
        ("UnitedHealthcare", "Private", "9900 Bren Rd E", "Minnetonka", "MN", "55343", "877-842-3210", 85000000.00, 7000000.00, 92000000.00),
    ]
    payers = []
    for name, own, addr, city, state, zip_c, phone, cov, uncov, rev in payer_defs:
        payers.append({
            "payer_id": str(uuid.uuid4()),
            "name": name,
            "ownership": own,
            "address": addr,
            "city": city,
            "state": state,
            "zip": zip_c,
            "phone": phone,
            "amount_covered": f"{cov:.2f}",
            "amount_uncovered": f"{uncov:.2f}",
            "revenue": f"{rev:.2f}"
        })
    with open(os.path.join(output_dir, "payers.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(payers[0].keys()))
        writer.writeheader()
        writer.writerows(payers)
    print("[OK] Saved payers.csv")

    # 3. Providers
    specialties = [
        "Internal Medicine", "Family Medicine", "Emergency Medicine", 
        "Cardiology", "Pediatrics", "Obstetrics & Gynecology", 
        "Orthopedic Surgery", "General Surgery", "Neurology", "Psychiatry"
    ]
    first_names_m = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles"]
    first_names_f = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]

    providers = []
    for i in range(120):
        gender = random.choice(["M", "F"])
        fname = random.choice(first_names_m if gender == "M" else first_names_f)
        lname = random.choice(last_names)
        org = random.choice(organizations)
        providers.append({
            "provider_id": str(uuid.uuid4()),
            "organization_id": org["organization_id"],
            "name": f"Dr. {fname} {lname}, MD",
            "gender": gender,
            "specialty": random.choice(specialties),
            "address": org["address"],
            "city": org["city"],
            "state": org["state"],
            "zip": org["zip"]
        })
    with open(os.path.join(output_dir, "providers.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(providers[0].keys()))
        writer.writeheader()
        writer.writerows(providers)
    print("[OK] Saved providers.csv")

    # 4. Patients
    cities = ["Boston", "Cambridge", "Worcester", "Springfield", "Lowell", "Brockton", "Quincy", "Lynn", "Newton", "Somerville"]
    races = ["white", "black", "asian", "native", "other"]
    ethnicities = ["nonhispanic", "hispanic"]
    
    patients = []
    base_date = date(2024, 12, 31)

    for i in range(num_patients):
        p_id = str(uuid.uuid4())
        gender = random.choice(["M", "F"])
        fname = random.choice(first_names_m if gender == "M" else first_names_f)
        lname = random.choice(last_names)
        age_years = random.choices(
            [random.randint(0, 17), random.randint(18, 35), random.randint(36, 64), random.randint(65, 88)],
            weights=[0.15, 0.28, 0.35, 0.22]
        )[0]
        birth_d = base_date - timedelta(days=int(age_years * 365.25) + random.randint(0, 360))
        
        # 4% deceased
        is_deceased = (random.random() < 0.04 and age_years > 50)
        death_d = None
        if is_deceased:
            death_d = birth_d + timedelta(days=int(age_years * 365.25))

        city = random.choice(cities)
        income = round(random.lognormvariate(10.8, 0.6), 2)

        patients.append({
            "patient_id": p_id,
            "birth_date": str(birth_d),
            "death_date": str(death_d) if death_d else "",
            "ssn": f"999-{random.randint(10,99)}-{random.randint(1000,9999)}",
            "drivers_license": f"S{random.randint(10000000,99999999)}",
            "passport": f"X{random.randint(10000000,99999999)}",
            "prefix": "Mr." if gender == "M" else "Ms.",
            "first_name": fname,
            "last_name": lname,
            "marital_status": "M" if age_years > 25 and random.random() < 0.6 else "S",
            "race": random.choice(races),
            "ethnicity": random.choice(ethnicities),
            "gender": gender,
            "birthplace": city,
            "address": f"{random.randint(10, 999)} {random.choice(['Main', 'Beacon', 'Commonwealth', 'Washington', 'Harvard', 'Boylston'])} St",
            "city": city,
            "state": "MA",
            "zip": f"021{random.randint(10, 99)}",
            "healthcare_expenses": "0.00",
            "healthcare_coverage": "0.00",
            "income": f"{income:.2f}",
            "_birth_date_obj": birth_d,
            "_death_date_obj": death_d
        })

    # 5. Encounters, Conditions, Medications, Procedures, Observations
    clinical_conditions_catalog = [
        ("44054006", "Type 2 Diabetes Mellitus", 650.00, ["860975", "855332"]), # Metformin, Glipizide
        ("38341003", "Essential Hypertension", 320.00, ["197361", "855324"]), # Amlodipine, Lisinopril
        ("59621000", "Essential Hypertension with CAD", 1200.00, ["197361", "310429"]), # Amlodipine, Atorvastatin
        ("233604007", "Pneumonia", 4200.00, ["197361", "309362"]), # Azithromycin
        ("195662009", "Acute Bronchitis", 280.00, ["309362"]),
        ("444814009", "Viral Sinusitis", 150.00, ["309362"]),
        ("15777000", "Prediabetes", 180.00, ["860975"]),
        ("44465007", "Sprain of Ankle", 450.00, ["5644"]), # Ibuprofen
        ("22298006", "Myocardial Infarction", 14500.00, ["310429", "855324"]), # Statin, Lisinopril
        ("36971009", "Hyperlipidemia", 220.00, ["310429"]),
        ("73211009", "Post-Traumatic Osteoarthritis", 890.00, ["5644"]),
        ("10509002", "Acute Bronchospasm", 620.00, ["309362"]),
    ]

    med_catalog = {
        "860975": ("Metformin hydrochloride 500 MG", 15.00),
        "855332": ("Glipizide 5 MG Oral Tablet", 22.00),
        "197361": ("Amlodipine 5 MG Oral Tablet", 18.00),
        "855324": ("Lisinopril 10 MG Oral Tablet", 14.00),
        "310429": ("Atorvastatin 20 MG Oral Tablet", 35.00),
        "309362": ("Azithromycin 250 MG Oral Tablet", 28.00),
        "5644":   ("Ibuprofen 400 MG Oral Tablet", 12.00)
    }

    procedure_catalog = [
        ("430193006", "Medication Reconciliation", 85.00),
        ("71020", "Chest X-Ray Single View", 220.00),
        ("93000", "Electrocardiogram Routine ECG with at least 12 leads", 160.00),
        ("41801008", "Dialysis procedure", 1800.00),
        ("36965003", "Diagnostic Ultrasound of Heart", 750.00),
        ("80053", "Comprehensive Metabolic Panel", 95.00),
        ("85025", "Blood count complete (CBC)", 45.00)
    ]

    encounters = []
    conditions = []
    medications = []
    procedures = []
    observations = []

    encounter_classes = ["ambulatory", "wellness", "emergency", "inpatient", "urgentcare"]
    class_weights = [0.45, 0.20, 0.18, 0.07, 0.10]

    # Pre-select chronic conditions for a fraction of patients
    chronic_pool = {}
    for p in patients:
        age = (base_date - p["_birth_date_obj"]).days // 365
        if age > 40 and random.random() < 0.45:
            cond = random.choice([clinical_conditions_catalog[0], clinical_conditions_catalog[1], clinical_conditions_catalog[9]])
            chronic_pool[p["patient_id"]] = cond

    for p in patients:
        p_id = p["patient_id"]
        birth_d = p["_birth_date_obj"]
        death_d = p["_death_date_obj"]
        patient_payer = random.choice(payers)

        # Number of lifetime encounters: 1 to 28 visits
        visit_count = random.choices([1, random.randint(2, 4), random.randint(5, 9), random.randint(10, 26)], weights=[0.25, 0.40, 0.22, 0.13])[0]
        
        # Generate visits over last 3 years (2022 to 2024)
        total_p_claim = 0.0
        total_p_coverage = 0.0

        for v in range(visit_count):
            enc_id = str(uuid.uuid4())
            e_class = random.choices(encounter_classes, weights=class_weights)[0]
            org = random.choice(organizations)
            prov = random.choice(providers)

            # Random date between 2022-01-01 and 2024-12-31 (or before death)
            start_offset_days = random.randint(0, 1095)
            enc_date = date(2022, 1, 1) + timedelta(days=start_offset_days)
            if death_d and enc_date > death_d:
                enc_date = death_d - timedelta(days=random.randint(1, 30))
            if enc_date < birth_d:
                enc_date = birth_d + timedelta(days=random.randint(1, 100))

            start_dt = datetime(enc_date.year, enc_date.month, enc_date.day, random.randint(7, 21), random.randint(0, 59))
            
            # Duration based on class
            if e_class == "emergency":
                dur_mins = random.randint(120, 600)
                base_cost = random.uniform(850.0, 2400.0)
            elif e_class == "inpatient":
                dur_mins = random.randint(1440, 7200) # 1 to 5 days
                base_cost = random.uniform(3500.0, 15000.0)
            elif e_class == "wellness":
                dur_mins = random.randint(30, 60)
                base_cost = random.uniform(120.0, 250.0)
            elif e_class == "urgentcare":
                dur_mins = random.randint(45, 120)
                base_cost = random.uniform(250.0, 550.0)
            else: # ambulatory
                dur_mins = random.randint(30, 90)
                base_cost = random.uniform(150.0, 400.0)

            stop_dt = start_dt + timedelta(minutes=dur_mins)

            # Condition assignment
            active_cond = None
            if p_id in chronic_pool and random.random() < 0.75:
                active_cond = chronic_pool[p_id]
            else:
                active_cond = random.choice(clinical_conditions_catalog)

            total_claim = base_cost + active_cond[2] * random.uniform(0.8, 1.2)
            
            # Payer coverage (70% - 95%)
            cov_ratio = random.uniform(0.70, 0.95) if patient_payer["ownership"] != "Uninsured" else 0.0
            payer_cov = total_claim * cov_ratio

            total_p_claim += total_claim
            total_p_coverage += payer_cov

            encounters.append({
                "encounter_id": enc_id,
                "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "stop_time": stop_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "patient_id": p_id,
                "organization_id": org["organization_id"],
                "provider_id": prov["provider_id"],
                "payer_id": patient_payer["payer_id"],
                "encounter_class": e_class,
                "code": active_cond[0],
                "description": f"{e_class.capitalize()} visit for {active_cond[1]}",
                "base_encounter_cost": f"{base_cost:.2f}",
                "total_claim_cost": f"{total_claim:.2f}",
                "payer_coverage": f"{payer_cov:.2f}",
                "reason_code": active_cond[0],
                "reason_description": active_cond[1]
            })

            # Record condition
            conditions.append({
                "start_date": enc_date.strftime("%Y-%m-%d"),
                "end_date": stop_dt.strftime("%Y-%m-%d") if e_class in ["emergency", "urgentcare"] and "Acute" in active_cond[1] else "",
                "patient_id": p_id,
                "encounter_id": enc_id,
                "code": active_cond[0],
                "description": active_cond[1]
            })

            # Associated Medications
            rx_candidates = active_cond[3]
            for rx_code in rx_candidates:
                rx_info = med_catalog[rx_code]
                med_cost = rx_info[1] * random.randint(1, 3)
                med_cov = med_cost * cov_ratio
                medications.append({
                    "start_date": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_date": (start_dt + timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S"),
                    "patient_id": p_id,
                    "payer_id": patient_payer["payer_id"],
                    "encounter_id": enc_id,
                    "code": rx_code,
                    "description": rx_info[0],
                    "base_cost": f"{rx_info[1]:.2f}",
                    "payer_coverage": f"{med_cov:.2f}",
                    "dispenses": random.randint(1, 3),
                    "total_cost": f"{med_cost:.2f}",
                    "reason_code": active_cond[0],
                    "reason_description": active_cond[1]
                })

            # Associated Procedures (for ~60% of encounters)
            if random.random() < 0.60:
                proc = random.choice(procedure_catalog)
                procedures.append({
                    "start_date": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_date": (start_dt + timedelta(minutes=random.randint(15, 60))).strftime("%Y-%m-%d %H:%M:%S"),
                    "patient_id": p_id,
                    "encounter_id": enc_id,
                    "code": proc[0],
                    "description": proc[1],
                    "base_cost": f"{proc[2]:.2f}",
                    "reason_code": active_cond[0],
                    "reason_description": active_cond[1]
                })

            # Observations (Blood pressure, BMI, Labs)
            sbp = random.randint(105, 160)
            dbp = random.randint(65, 100)
            bmi = round(random.uniform(19.0, 38.0), 1)

            observations.append({
                "obs_date": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "patient_id": p_id,
                "encounter_id": enc_id,
                "category": "vital-signs",
                "code": "8480-6",
                "description": "Systolic Blood Pressure",
                "value": str(sbp),
                "units": "mmHg",
                "obs_type": "numeric"
            })
            observations.append({
                "obs_date": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "patient_id": p_id,
                "encounter_id": enc_id,
                "category": "vital-signs",
                "code": "8462-4",
                "description": "Diastolic Blood Pressure",
                "value": str(dbp),
                "units": "mmHg",
                "obs_type": "numeric"
            })
            observations.append({
                "obs_date": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "patient_id": p_id,
                "encounter_id": enc_id,
                "category": "vital-signs",
                "code": "39156-5",
                "description": "Body Mass Index",
                "value": str(bmi),
                "units": "kg/m2",
                "obs_type": "numeric"
            })

        p["healthcare_expenses"] = f"{total_p_claim:.2f}"
        p["healthcare_coverage"] = f"{total_p_coverage:.2f}"

    # Clean internal temporary patient keys
    for p in patients:
        del p["_birth_date_obj"]
        del p["_death_date_obj"]

    # Write patients.csv
    with open(os.path.join(output_dir, "patients.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(patients[0].keys()))
        writer.writeheader()
        writer.writerows(patients)
    print(f"[OK] Saved patients.csv ({len(patients):,} rows)")

    # Write encounters.csv
    with open(os.path.join(output_dir, "encounters.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(encounters[0].keys()))
        writer.writeheader()
        writer.writerows(encounters)
    print(f"[OK] Saved encounters.csv ({len(encounters):,} rows)")

    # Write conditions.csv
    with open(os.path.join(output_dir, "conditions.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(conditions[0].keys()))
        writer.writeheader()
        writer.writerows(conditions)
    print(f"[OK] Saved conditions.csv ({len(conditions):,} rows)")

    # Write medications.csv
    with open(os.path.join(output_dir, "medications.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(medications[0].keys()))
        writer.writeheader()
        writer.writerows(medications)
    print(f"[OK] Saved medications.csv ({len(medications):,} rows)")

    # Write procedures.csv
    with open(os.path.join(output_dir, "procedures.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(procedures[0].keys()))
        writer.writeheader()
        writer.writerows(procedures)
    print(f"[OK] Saved procedures.csv ({len(procedures):,} rows)")

    # Write observations.csv
    with open(os.path.join(output_dir, "observations.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(observations[0].keys()))
        writer.writeheader()
        writer.writerows(observations)
    print(f"[OK] Saved observations.csv ({len(observations):,} rows)")

    # Empty/Template careplans & immunizations
    with open(os.path.join(output_dir, "careplans.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["careplan_id", "start_date", "end_date", "patient_id", "encounter_id", "code", "description", "reason_code", "reason_description"])
    print("[OK] Saved careplans.csv")

    with open(os.path.join(output_dir, "immunizations.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date_administered", "patient_id", "encounter_id", "code", "description", "cost"])
    print("[OK] Saved immunizations.csv")

    print("\nDataset generation completed successfully.")

if __name__ == "__main__":
    generate_dataset()
