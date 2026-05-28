-- Unity Catalog function definitions for the financial risk agent.
-- These functions are registered as tools available to the agent via
-- the Databricks AI Gateway function-calling interface.
--
-- Usage: databricks sql execute --file sql/create_uc_functions.sql
-- Variables: ${catalog}, ${schema}

-- ---------------------------------------------------------------------------
-- get_risk_exposure: query counterparty risk data
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.get_risk_exposure(
    counterparty_name STRING COMMENT 'Name of the counterparty to look up'
)
RETURNS TABLE (
    counterparty_name STRING,
    risk_tier STRING,
    total_exposure_usd DOUBLE,
    credit_rating STRING,
    default_probability DOUBLE,
    sector STRING,
    country STRING,
    last_updated DATE
)
COMMENT 'Retrieve counterparty risk exposure including risk tier, total exposure, credit rating, and default probability.'
RETURN
    SELECT
        counterparty_name,
        risk_tier,
        total_exposure_usd,
        credit_rating,
        default_probability,
        sector,
        country,
        last_updated
    FROM ${catalog}.${schema}.gold_risk_exposure
    WHERE LOWER(gold_risk_exposure.counterparty_name) = LOWER(get_risk_exposure.counterparty_name);

-- ---------------------------------------------------------------------------
-- get_financial_ratios: query counterparty financial health indicators
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.get_financial_ratios(
    counterparty_name STRING COMMENT 'Name of the counterparty to look up'
)
RETURNS TABLE (
    counterparty_name STRING,
    debt_to_equity DOUBLE,
    current_ratio DOUBLE,
    interest_coverage DOUBLE,
    return_on_equity DOUBLE,
    revenue_growth_pct DOUBLE,
    last_updated DATE
)
COMMENT 'Retrieve financial ratios for a counterparty including debt-to-equity, current ratio, interest coverage, and return on equity.'
RETURN
    SELECT
        counterparty_name,
        debt_to_equity,
        current_ratio,
        interest_coverage,
        return_on_equity,
        revenue_growth_pct,
        last_updated
    FROM ${catalog}.${schema}.gold_financial_ratios
    WHERE LOWER(gold_financial_ratios.counterparty_name) = LOWER(get_financial_ratios.counterparty_name);

-- ---------------------------------------------------------------------------
-- get_portfolio_summary: aggregate portfolio metrics by sector
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.get_portfolio_summary()
RETURNS TABLE (
    sector STRING,
    num_counterparties INT,
    total_exposure_usd DOUBLE,
    concentration_pct DOUBLE,
    avg_risk_score DOUBLE,
    dominant_risk_tier STRING
)
COMMENT 'Retrieve portfolio summary showing concentration by sector, total exposure, number of counterparties, and average risk score.'
RETURN
    SELECT
        sector,
        num_counterparties,
        total_exposure_usd,
        concentration_pct,
        avg_risk_score,
        dominant_risk_tier
    FROM ${catalog}.${schema}.gold_portfolio_summary
    ORDER BY concentration_pct DESC;

-- ---------------------------------------------------------------------------
-- get_portfolios: list all available portfolios
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.get_portfolios()
RETURNS TABLE (
    portfolio_id STRING,
    portfolio_name STRING,
    strategy STRING,
    manager STRING,
    created_date DATE
)
COMMENT 'List all available portfolios with their strategy and manager.'
RETURN
    SELECT
        portfolio_id,
        portfolio_name,
        strategy,
        manager,
        created_date
    FROM ${catalog}.${schema}.gold_portfolios
    ORDER BY portfolio_name;

-- ---------------------------------------------------------------------------
-- get_portfolio_counterparties: get all counterparties in a portfolio with risk data
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.get_portfolio_counterparties(
    p_portfolio_id STRING COMMENT 'Portfolio ID to look up (e.g., PF-ALPHA)'
)
RETURNS TABLE (
    portfolio_name STRING,
    counterparty_name STRING,
    allocation_pct DOUBLE,
    position_type STRING,
    risk_tier STRING,
    total_exposure_usd DOUBLE,
    credit_rating STRING,
    default_probability DOUBLE,
    sector STRING
)
COMMENT 'Retrieve all counterparties in a portfolio with their allocation, risk tier, exposure, and credit data.'
RETURN
    SELECT
        p.portfolio_name,
        h.counterparty_name,
        h.allocation_pct,
        h.position_type,
        r.risk_tier,
        r.total_exposure_usd,
        r.credit_rating,
        r.default_probability,
        r.sector
    FROM ${catalog}.${schema}.gold_portfolio_holdings h
    JOIN ${catalog}.${schema}.gold_portfolios p
        ON h.portfolio_id = p.portfolio_id
    JOIN ${catalog}.${schema}.gold_risk_exposure r
        ON LOWER(h.counterparty_name) = LOWER(r.counterparty_name)
    WHERE LOWER(h.portfolio_id) = LOWER(get_portfolio_counterparties.p_portfolio_id)
    ORDER BY h.allocation_pct DESC;

-- ---------------------------------------------------------------------------
-- get_portfolio_financial_health: counterparties + risk + financial ratios in one call
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION ${catalog}.${schema}.get_portfolio_financial_health(
    p_portfolio_id STRING COMMENT 'Portfolio ID to look up (e.g., PF-ALPHA)'
)
RETURNS TABLE (
    portfolio_name STRING,
    counterparty_name STRING,
    allocation_pct DOUBLE,
    risk_tier STRING,
    total_exposure_usd DOUBLE,
    credit_rating STRING,
    default_probability DOUBLE,
    sector STRING,
    debt_to_equity DOUBLE,
    current_ratio DOUBLE,
    interest_coverage DOUBLE,
    return_on_equity DOUBLE,
    revenue_growth_pct DOUBLE
)
COMMENT 'Retrieve all counterparties in a portfolio with risk exposure AND financial ratios in a single call. Avoids N+1 queries.'
RETURN
    SELECT
        p.portfolio_name,
        h.counterparty_name,
        h.allocation_pct,
        r.risk_tier,
        r.total_exposure_usd,
        r.credit_rating,
        r.default_probability,
        r.sector,
        f.debt_to_equity,
        f.current_ratio,
        f.interest_coverage,
        f.return_on_equity,
        f.revenue_growth_pct
    FROM ${catalog}.${schema}.gold_portfolio_holdings h
    JOIN ${catalog}.${schema}.gold_portfolios p
        ON h.portfolio_id = p.portfolio_id
    JOIN ${catalog}.${schema}.gold_risk_exposure r
        ON LOWER(h.counterparty_name) = LOWER(r.counterparty_name)
    JOIN ${catalog}.${schema}.gold_financial_ratios f
        ON LOWER(h.counterparty_name) = LOWER(f.counterparty_name)
    WHERE LOWER(h.portfolio_id) = LOWER(get_portfolio_financial_health.p_portfolio_id)
    ORDER BY h.allocation_pct DESC;
