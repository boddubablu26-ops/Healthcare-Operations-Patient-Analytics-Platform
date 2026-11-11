-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 03_constraints.sql
-- Description: Foreign keys, temporal validity, and financial check constraints
-- ============================================================================

-- 1. Foreign Key Constraints on Encounters
ALTER TABLE raw_synthea.encounters
    ADD CONSTRAINT fk_encounters_patient
    FOREIGN KEY (patient_id) REFERENCES raw_synthea.patients(patient_id)
    ON DELETE CASCADE;

ALTER TABLE raw_synthea.encounters
    ADD CONSTRAINT fk_encounters_organization
    FOREIGN KEY (organization_id) REFERENCES raw_synthea.organizations(organization_id)
    ON DELETE SET NULL;

ALTER TABLE raw_synthea.encounters
    ADD CONSTRAINT fk_encounters_provider
    FOREIGN KEY (provider_id) REFERENCES raw_synthea.providers(provider_id)
    ON DELETE SET NULL;

ALTER TABLE raw_synthea.encounters
    ADD CONSTRAINT fk_encounters_payer
    FOREIGN KEY (payer_id) REFERENCES raw_synthea.payers(payer_id)
    ON DELETE SET NULL;

-- 2. Foreign Key Constraints on Conditions
ALTER TABLE raw_synthea.conditions
    ADD CONSTRAINT fk_conditions_patient
    FOREIGN KEY (patient_id) REFERENCES raw_synthea.patients(patient_id)
    ON DELETE CASCADE;

ALTER TABLE raw_synthea.conditions
    ADD CONSTRAINT fk_conditions_encounter
    FOREIGN KEY (encounter_id) REFERENCES raw_synthea.encounters(encounter_id)
    ON DELETE CASCADE;

-- 3. Foreign Key Constraints on Medications
ALTER TABLE raw_synthea.medications
    ADD CONSTRAINT fk_medications_patient
    FOREIGN KEY (patient_id) REFERENCES raw_synthea.patients(patient_id)
    ON DELETE CASCADE;

ALTER TABLE raw_synthea.medications
    ADD CONSTRAINT fk_medications_encounter
    FOREIGN KEY (encounter_id) REFERENCES raw_synthea.encounters(encounter_id)
    ON DELETE CASCADE;

ALTER TABLE raw_synthea.medications
    ADD CONSTRAINT fk_medications_payer
    FOREIGN KEY (payer_id) REFERENCES raw_synthea.payers(payer_id)
    ON DELETE SET NULL;

-- 4. Foreign Key Constraints on Procedures
ALTER TABLE raw_synthea.procedures
    ADD CONSTRAINT fk_procedures_patient
    FOREIGN KEY (patient_id) REFERENCES raw_synthea.patients(patient_id)
    ON DELETE CASCADE;

ALTER TABLE raw_synthea.procedures
    ADD CONSTRAINT fk_procedures_encounter
    FOREIGN KEY (encounter_id) REFERENCES raw_synthea.encounters(encounter_id)
    ON DELETE CASCADE;

-- 5. Foreign Key Constraints on Observations
ALTER TABLE raw_synthea.observations
    ADD CONSTRAINT fk_observations_patient
    FOREIGN KEY (patient_id) REFERENCES raw_synthea.patients(patient_id)
    ON DELETE CASCADE;

ALTER TABLE raw_synthea.observations
    ADD CONSTRAINT fk_observations_encounter
    FOREIGN KEY (encounter_id) REFERENCES raw_synthea.encounters(encounter_id)
    ON DELETE CASCADE;

-- 6. Temporal Check Constraints
ALTER TABLE raw_synthea.encounters
    ADD CONSTRAINT chk_encounter_dates
    CHECK (stop_time IS NULL OR stop_time >= start_time);

ALTER TABLE raw_synthea.conditions
    ADD CONSTRAINT chk_condition_dates
    CHECK (end_date IS NULL OR end_date >= start_date);

ALTER TABLE raw_synthea.medications
    ADD CONSTRAINT chk_medication_dates
    CHECK (end_date IS NULL OR end_date >= start_date);

-- 7. Financial Check Constraints (Non-negative costs)
ALTER TABLE raw_synthea.encounters
    ADD CONSTRAINT chk_encounter_costs_non_negative
    CHECK (base_encounter_cost >= 0 AND total_claim_cost >= 0 AND payer_coverage >= 0);

ALTER TABLE raw_synthea.medications
    ADD CONSTRAINT chk_medication_costs_non_negative
    CHECK (base_cost >= 0 AND total_cost >= 0 AND payer_coverage >= 0);
