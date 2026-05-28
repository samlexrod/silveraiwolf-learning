-- Create the financial risk schema in Unity Catalog
-- Usage: databricks sql execute --file sql/create_schema.sql
-- Variables: ${catalog}, ${schema}

CREATE SCHEMA IF NOT EXISTS ${catalog}.${schema};
