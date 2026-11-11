-- ============================================================================
-- Project: Healthcare Operations & Patient Analytics Platform
-- Script: 01_create_database.sql
-- Description: Database initialization, schema creation, extensions
-- ============================================================================

-- Ensure uuid extension is available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create dedicated schemas
CREATE SCHEMA IF NOT EXISTS raw_synthea;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO analytics, raw_synthea, public;

COMMENT ON SCHEMA raw_synthea IS 'Staging schema containing normalized Synthea synthetic healthcare tables';
COMMENT ON SCHEMA analytics IS 'Dimensional star schema, analytical views, and reporting layers';
