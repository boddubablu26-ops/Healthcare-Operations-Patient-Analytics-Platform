-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 02_create_tables.sql
-- Description: Staging table DDL for Synthea synthetic health records
-- ============================================================================

DROP TABLE IF EXISTS raw_synthea.observations CASCADE;
DROP TABLE IF EXISTS raw_synthea.procedures CASCADE;
DROP TABLE IF EXISTS raw_synthea.medications CASCADE;
DROP TABLE IF EXISTS raw_synthea.conditions CASCADE;
DROP TABLE IF EXISTS raw_synthea.careplans CASCADE;
DROP TABLE IF EXISTS raw_synthea.immunizations CASCADE;
DROP TABLE IF EXISTS raw_synthea.encounters CASCADE;
DROP TABLE IF EXISTS raw_synthea.patients CASCADE;
DROP TABLE IF EXISTS raw_synthea.providers CASCADE;
DROP TABLE IF EXISTS raw_synthea.organizations CASCADE;
DROP TABLE IF EXISTS raw_synthea.payers CASCADE;

-- 1. Organizations
CREATE TABLE raw_synthea.organizations (
    organization_id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(50),
    zip VARCHAR(20),
    phone VARCHAR(50),
    revenue NUMERIC(14, 2),
    utilization INTEGER
);

-- 2. Payers
CREATE TABLE raw_synthea.payers (
    payer_id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    ownership VARCHAR(50),
    address VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(50),
    zip VARCHAR(20),
    phone VARCHAR(50),
    amount_covered NUMERIC(14, 2) DEFAULT 0.00,
    amount_uncovered NUMERIC(14, 2) DEFAULT 0.00,
    revenue NUMERIC(14, 2) DEFAULT 0.00
);

-- 3. Providers
CREATE TABLE raw_synthea.providers (
    provider_id UUID PRIMARY KEY,
    organization_id UUID,
    name VARCHAR(200) NOT NULL,
    gender VARCHAR(10),
    specialty VARCHAR(100),
    address VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(50),
    zip VARCHAR(20)
);

-- 4. Patients
CREATE TABLE raw_synthea.patients (
    patient_id UUID PRIMARY KEY,
    birth_date DATE NOT NULL,
    death_date DATE,
    ssn VARCHAR(30),
    drivers_license VARCHAR(30),
    passport VARCHAR(30),
    prefix VARCHAR(20),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    marital_status VARCHAR(20),
    race VARCHAR(50),
    ethnicity VARCHAR(50),
    gender VARCHAR(10) NOT NULL,
    birthplace VARCHAR(200),
    address VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(50),
    zip VARCHAR(20),
    healthcare_expenses NUMERIC(12, 2) DEFAULT 0.00,
    healthcare_coverage NUMERIC(12, 2) DEFAULT 0.00,
    income NUMERIC(12, 2) DEFAULT 0.00
);

-- 5. Encounters
CREATE TABLE raw_synthea.encounters (
    encounter_id UUID PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    stop_time TIMESTAMP,
    patient_id UUID NOT NULL,
    organization_id UUID,
    provider_id UUID,
    payer_id UUID,
    encounter_class VARCHAR(50) NOT NULL,
    code VARCHAR(50),
    description TEXT,
    base_encounter_cost NUMERIC(12, 2) DEFAULT 0.00,
    total_claim_cost NUMERIC(12, 2) DEFAULT 0.00,
    payer_coverage NUMERIC(12, 2) DEFAULT 0.00,
    reason_code VARCHAR(50),
    reason_description TEXT
);

-- 6. Conditions
CREATE TABLE raw_synthea.conditions (
    start_date DATE NOT NULL,
    end_date DATE,
    patient_id UUID NOT NULL,
    encounter_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT NOT NULL
);

-- 7. Medications
CREATE TABLE raw_synthea.medications (
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    patient_id UUID NOT NULL,
    payer_id UUID,
    encounter_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    base_cost NUMERIC(12, 2) DEFAULT 0.00,
    payer_coverage NUMERIC(12, 2) DEFAULT 0.00,
    dispenses INTEGER DEFAULT 1,
    total_cost NUMERIC(12, 2) DEFAULT 0.00,
    reason_code VARCHAR(50),
    reason_description TEXT
);

-- 8. Procedures
CREATE TABLE raw_synthea.procedures (
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    patient_id UUID NOT NULL,
    encounter_id UUID NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    base_cost NUMERIC(12, 2) DEFAULT 0.00,
    reason_code VARCHAR(50),
    reason_description TEXT
);

-- 9. Observations
CREATE TABLE raw_synthea.observations (
    obs_date TIMESTAMP NOT NULL,
    patient_id UUID NOT NULL,
    encounter_id UUID,
    category VARCHAR(50),
    code VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    value TEXT,
    units VARCHAR(50),
    obs_type VARCHAR(50)
);

-- 10. Care Plans
CREATE TABLE raw_synthea.careplans (
    careplan_id UUID,
    start_date DATE NOT NULL,
    end_date DATE,
    patient_id UUID NOT NULL,
    encounter_id UUID,
    code VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    reason_code VARCHAR(50),
    reason_description TEXT
);

-- 11. Immunizations
CREATE TABLE raw_synthea.immunizations (
    date_administered TIMESTAMP NOT NULL,
    patient_id UUID NOT NULL,
    encounter_id UUID,
    code VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    cost NUMERIC(12, 2) DEFAULT 0.00
);
