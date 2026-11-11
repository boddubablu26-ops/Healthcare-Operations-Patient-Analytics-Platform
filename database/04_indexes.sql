-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 04_indexes.sql
-- Description: Performance B-Tree and Composite Indexes
-- ============================================================================

-- Staging & Dimensional Core Lookups
CREATE INDEX IF NOT EXISTS idx_patients_pk ON raw_synthea.patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_organizations_pk ON raw_synthea.organizations(organization_id);
CREATE INDEX IF NOT EXISTS idx_providers_pk ON raw_synthea.providers(provider_id);
CREATE INDEX IF NOT EXISTS idx_payers_pk ON raw_synthea.payers(payer_id);

-- Encounters Relational Keys & High-Frequency Dimensions
CREATE INDEX IF NOT EXISTS idx_encounters_patient_id ON raw_synthea.encounters(patient_id);
CREATE INDEX IF NOT EXISTS idx_encounters_org_id ON raw_synthea.encounters(organization_id);
CREATE INDEX IF NOT EXISTS idx_encounters_provider_id ON raw_synthea.encounters(provider_id);
CREATE INDEX IF NOT EXISTS idx_encounters_payer_id ON raw_synthea.encounters(payer_id);
CREATE INDEX IF NOT EXISTS idx_encounters_class ON raw_synthea.encounters(encounter_class);
CREATE INDEX IF NOT EXISTS idx_encounters_start_time ON raw_synthea.encounters(start_time);

-- Composite Index for Time-Series, Class, and Financial Aggregations
CREATE INDEX IF NOT EXISTS idx_encounters_time_class_cost 
ON raw_synthea.encounters(start_time, encounter_class, total_claim_cost);

-- Clinical Child Table Foreign Keys & Codes
CREATE INDEX IF NOT EXISTS idx_conditions_patient_id ON raw_synthea.conditions(patient_id);
CREATE INDEX IF NOT EXISTS idx_conditions_encounter_id ON raw_synthea.conditions(encounter_id);
CREATE INDEX IF NOT EXISTS idx_conditions_code ON raw_synthea.conditions(code);

CREATE INDEX IF NOT EXISTS idx_medications_patient_id ON raw_synthea.medications(patient_id);
CREATE INDEX IF NOT EXISTS idx_medications_encounter_id ON raw_synthea.medications(encounter_id);
CREATE INDEX IF NOT EXISTS idx_medications_code ON raw_synthea.medications(code);

CREATE INDEX IF NOT EXISTS idx_procedures_patient_id ON raw_synthea.procedures(patient_id);
CREATE INDEX IF NOT EXISTS idx_procedures_encounter_id ON raw_synthea.procedures(encounter_id);
CREATE INDEX IF NOT EXISTS idx_procedures_code ON raw_synthea.procedures(code);

CREATE INDEX IF NOT EXISTS idx_observations_patient_id ON raw_synthea.observations(patient_id);
CREATE INDEX IF NOT EXISTS idx_observations_encounter_id ON raw_synthea.observations(encounter_id);
CREATE INDEX IF NOT EXISTS idx_observations_code ON raw_synthea.observations(code);
