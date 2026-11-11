# Healthcare Data Dictionary & Schema Reference
## Synthetic Health Records (Synthea™ Relational Model)

---

## 1. Schema Conventions
- All primary keys use standard UUIDs.
- Monetary quantities use `NUMERIC(12, 2)` representing USD ($).
- Timestamps conform to ISO 8601 (`YYYY-MM-DD HH:MI:SS`).
- Staging schema: `raw_synthea`
- Dimensional analytical schema: `analytics`

---

## 2. Table Specifications

### 2.1 `raw_synthea.patients`
- **Grain**: 1 row = 1 individual synthetic patient
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `patient_id` | UUID | NO | Primary key |
| `birth_date` | DATE | NO | Patient date of birth |
| `death_date` | DATE | YES | Patient date of death (NULL if alive) |
| `ssn` | VARCHAR(20) | YES | Synthetic SSN |
| `drivers_license` | VARCHAR(20) | YES | Synthetic driver's license |
| `passport` | VARCHAR(20) | YES | Synthetic passport number |
| `prefix` | VARCHAR(10) | YES | Name prefix (Mr., Ms., Dr.) |
| `first_name` | VARCHAR(50) | NO | First name |
| `last_name` | VARCHAR(50) | NO | Last name |
| `marital_status` | VARCHAR(10) | YES | Marital status (M, S) |
| `race` | VARCHAR(50) | YES | Patient race category |
| `ethnicity` | VARCHAR(50) | YES | Patient ethnicity |
| `gender` | VARCHAR(10) | NO | Biological gender (M, F) |
| `birthplace` | VARCHAR(100) | YES | City/Country of birth |
| `address` | VARCHAR(100) | YES | Residential street address |
| `city` | VARCHAR(50) | YES | Residential city |
| `state` | VARCHAR(50) | YES | State of residence |
| `zip` | VARCHAR(20) | YES | Postal zip code |
| `healthcare_expenses` | NUMERIC(12,2) | YES | Cumulative healthcare expenses |
| `healthcare_coverage` | NUMERIC(12,2) | YES | Cumulative insurance coverage |
| `income` | NUMERIC(12,2) | YES | Annual household income |

---

### 2.2 `raw_synthea.encounters`
- **Grain**: 1 row = 1 healthcare encounter / visit event
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `encounter_id` | UUID | NO | Primary key |
| `start_time` | TIMESTAMP | NO | Admission / visit start datetime |
| `stop_time` | TIMESTAMP | YES | Discharge / visit end datetime |
| `patient_id` | UUID | NO | Foreign key to `patients.patient_id` |
| `organization_id` | UUID | YES | Foreign key to `organizations.organization_id` |
| `provider_id` | UUID | YES | Foreign key to `providers.provider_id` |
| `payer_id` | UUID | YES | Foreign key to `payers.payer_id` |
| `encounter_class` | VARCHAR(50) | NO | Encounter class (ambulatory, emergency, inpatient, wellness, urgentcare) |
| `code` | VARCHAR(50) | YES | Clinical billing code (SNOMED-CT) |
| `description` | TEXT | YES | Clinical encounter description |
| `base_encounter_cost`| NUMERIC(12,2) | NO | Baseline facility cost |
| `total_claim_cost` | NUMERIC(12,2) | NO | Total claim cost submitted |
| `payer_coverage` | NUMERIC(12,2) | NO | Amount reimbursed by payer |
| `reason_code` | VARCHAR(50) | YES | Primary diagnosis/reason code |
| `reason_description` | TEXT | YES | Text description of reason |

---

### 2.3 `raw_synthea.conditions`
- **Grain**: 1 row = 1 diagnosed condition for a patient during an encounter
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `start_date` | DATE | NO | Onset date of condition |
| `end_date` | DATE | YES | Resolution date (NULL if chronic/active) |
| `patient_id` | UUID | NO | Foreign key to `patients.patient_id` |
| `encounter_id` | UUID | NO | Foreign key to `encounters.encounter_id` |
| `code` | VARCHAR(50) | NO | SNOMED-CT diagnosis code |
| `description` | TEXT | NO | Clinical diagnosis description |

---

### 2.4 `raw_synthea.medications`
- **Grain**: 1 row = 1 medication order / dispense event
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `start_date` | TIMESTAMP | NO | Prescription start datetime |
| `end_date` | TIMESTAMP | YES | Prescription end datetime |
| `patient_id` | UUID | NO | Foreign key to `patients.patient_id` |
| `payer_id` | UUID | YES | Foreign key to `payers.payer_id` |
| `encounter_id` | UUID | NO | Foreign key to `encounters.encounter_id` |
| `code` | VARCHAR(50) | NO | RxNorm pharmaceutical code |
| `description` | TEXT | NO | Drug brand/generic name & dosage |
| `base_cost` | NUMERIC(12,2) | NO | Unit drug baseline cost |
| `payer_coverage` | NUMERIC(12,2) | NO | Payer covered drug benefit |
| `dispenses` | INTEGER | NO | Number of prescription refills/dispenses |
| `total_cost` | NUMERIC(12,2) | NO | Aggregate medication cost |
| `reason_code` | VARCHAR(50) | YES | Associated diagnosis code |
| `reason_description` | TEXT | YES | Associated diagnosis description |

---

### 2.5 `raw_synthea.procedures`
- **Grain**: 1 row = 1 clinical or surgical procedure
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `start_date` | TIMESTAMP | NO | Procedure datetime |
| `end_date` | TIMESTAMP | YES | Procedure completion datetime |
| `patient_id` | UUID | NO | Foreign key to `patients.patient_id` |
| `encounter_id` | UUID | NO | Foreign key to `encounters.encounter_id` |
| `code` | VARCHAR(50) | NO | SNOMED-CT procedure code |
| `description` | TEXT | NO | Procedure description |
| `base_cost` | NUMERIC(12,2) | NO | Cost of procedure |
| `reason_code` | VARCHAR(50) | YES | Reason code for procedure |
| `reason_description` | TEXT | YES | Reason description |

---

### 2.6 `raw_synthea.observations`
- **Grain**: 1 row = 1 laboratory or clinical observation measurement
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `obs_date` | TIMESTAMP | NO | Measurement timestamp |
| `patient_id` | UUID | NO | Foreign key to `patients.patient_id` |
| `encounter_id` | UUID | YES | Foreign key to `encounters.encounter_id` |
| `category` | VARCHAR(50) | YES | vital-signs, laboratory, survey |
| `code` | VARCHAR(50) | NO | LOINC observation code |
| `description` | TEXT | NO | Clinical observation name |
| `value` | TEXT | YES | Raw observed value |
| `units` | VARCHAR(50) | YES | Unit of measurement (mmHg, mg/dL, etc.) |
| `obs_type` | VARCHAR(50) | YES | Numeric or categorical |

---

### 2.7 `raw_synthea.organizations`
- **Grain**: 1 row = 1 healthcare facility / hospital / clinic
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `organization_id` | UUID | NO | Primary key |
| `name` | VARCHAR(100) | NO | Healthcare facility name |
| `address` | VARCHAR(100) | YES | Physical street address |
| `city` | VARCHAR(50) | YES | Facility city |
| `state` | VARCHAR(50) | YES | Facility state |
| `zip` | VARCHAR(20) | YES | Postal zip code |
| `phone` | VARCHAR(30) | YES | Contact telephone |
| `revenue` | NUMERIC(14,2) | YES | Facility annual revenue |
| `utilization` | INTEGER | YES | Facility bed / patient capacity rating |

---

### 2.8 `raw_synthea.providers`
- **Grain**: 1 row = 1 clinician / physician
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `provider_id` | UUID | NO | Primary key |
| `organization_id` | UUID | YES | Affiliated organization |
| `name` | VARCHAR(100) | NO | Provider name |
| `gender` | VARCHAR(10) | YES | Biological gender |
| `specialty` | VARCHAR(100) | YES | Clinical specialty (Internal Medicine, Emergency, etc.) |
| `address` | VARCHAR(100) | YES | Practice address |
| `city` | VARCHAR(50) | YES | Practice city |
| `state` | VARCHAR(50) | YES | Practice state |
| `zip` | VARCHAR(20) | YES | Practice zip code |

---

### 2.9 `raw_synthea.payers`
- **Grain**: 1 row = 1 insurance payer / coverage organization
| Column | Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `payer_id` | UUID | NO | Primary key |
| `name` | VARCHAR(100) | NO | Payer name (Medicare, Medicaid, Blue Cross, etc.) |
| `ownership` | VARCHAR(50) | YES | Ownership model (Government, Private, Non-Profit) |
| `address` | VARCHAR(100) | YES | Payer address |
| `city` | VARCHAR(50) | YES | Payer city |
| `state` | VARCHAR(50) | YES | Payer state |
| `zip` | VARCHAR(20) | YES | Postal zip code |
| `phone` | VARCHAR(30) | YES | Customer service telephone |
| `amount_covered` | NUMERIC(14,2) | YES | Cumulative covered expenditure |
| `amount_uncovered` | NUMERIC(14,2) | YES | Cumulative uncovered expenditure |
| `revenue` | NUMERIC(14,2) | YES | Annual payer revenue |
