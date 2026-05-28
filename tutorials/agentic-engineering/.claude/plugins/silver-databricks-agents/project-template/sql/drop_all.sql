-- Drop all objects created by the financial risk agent project.
-- Use this for a clean teardown during development or cleanup.
--
-- Usage: databricks sql execute --file sql/drop_all.sql
-- Variables: ${catalog}, ${schema}

-- Drop Unity Catalog functions
DROP FUNCTION IF EXISTS ${catalog}.${schema}.get_risk_exposure;
DROP FUNCTION IF EXISTS ${catalog}.${schema}.get_financial_ratios;
DROP FUNCTION IF EXISTS ${catalog}.${schema}.get_portfolio_summary;

-- Drop Gold tables
DROP TABLE IF EXISTS ${catalog}.${schema}.gold_risk_exposure;
DROP TABLE IF EXISTS ${catalog}.${schema}.gold_financial_ratios;
DROP TABLE IF EXISTS ${catalog}.${schema}.gold_portfolio_summary;

-- Optionally drop the schema (uncomment if you want full cleanup)
-- DROP SCHEMA IF EXISTS ${catalog}.${schema} CASCADE;
