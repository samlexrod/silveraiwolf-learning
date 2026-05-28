-- Create Gold tables for the financial risk domain.
-- These tables hold curated, business-ready data queried by the agent's tools.
--
-- Usage: databricks sql execute --file sql/create_gold_tables.sql
-- Variables: ${catalog}, ${schema}

-- ---------------------------------------------------------------------------
-- gold_risk_exposure: counterparty-level risk metrics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.gold_risk_exposure (
    counterparty_name STRING NOT NULL COMMENT 'Legal entity name',
    risk_tier STRING NOT NULL COMMENT 'Risk classification: LOW, MEDIUM, HIGH, CRITICAL',
    total_exposure_usd DOUBLE NOT NULL COMMENT 'Total credit exposure in USD',
    credit_rating STRING NOT NULL COMMENT 'External credit rating (S&P scale)',
    default_probability DOUBLE NOT NULL COMMENT 'Estimated probability of default (0-1)',
    sector STRING COMMENT 'Industry sector',
    country STRING COMMENT 'Country of domicile (ISO 2-letter)',
    last_updated DATE COMMENT 'Date of last data refresh'
)
COMMENT 'Gold table: counterparty risk exposure metrics aggregated from Silver layer';

-- ---------------------------------------------------------------------------
-- gold_financial_ratios: key financial health indicators
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.gold_financial_ratios (
    counterparty_name STRING NOT NULL COMMENT 'Legal entity name',
    debt_to_equity DOUBLE NOT NULL COMMENT 'Total debt / total equity ratio',
    current_ratio DOUBLE NOT NULL COMMENT 'Current assets / current liabilities',
    interest_coverage DOUBLE NOT NULL COMMENT 'EBIT / interest expense',
    return_on_equity DOUBLE NOT NULL COMMENT 'Net income / shareholder equity',
    revenue_growth_pct DOUBLE NOT NULL COMMENT 'Year-over-year revenue growth percentage',
    last_updated DATE COMMENT 'Date of last data refresh'
)
COMMENT 'Gold table: counterparty financial health ratios from latest filings';

-- ---------------------------------------------------------------------------
-- gold_portfolio_summary: sector-level portfolio aggregates
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ${catalog}.${schema}.gold_portfolio_summary (
    sector STRING NOT NULL COMMENT 'Industry sector',
    num_counterparties INT NOT NULL COMMENT 'Number of counterparties in sector',
    total_exposure_usd DOUBLE NOT NULL COMMENT 'Sum of exposure across sector',
    concentration_pct DOUBLE NOT NULL COMMENT 'Sector exposure as % of total portfolio',
    avg_risk_score DOUBLE NOT NULL COMMENT 'Average risk score (1-10 scale)',
    dominant_risk_tier STRING NOT NULL COMMENT 'Most common risk tier in sector'
)
COMMENT 'Gold table: portfolio concentration metrics by sector';
