-- Seed data for the financial risk streaming tutorial
-- Creates tables with REPLICA IDENTITY FULL for Debezium CDC

BEGIN;

-- ============================================================
-- Counterparties
-- ============================================================

CREATE TABLE IF NOT EXISTS counterparties (
    counterparty_id    VARCHAR(10) PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    sector             VARCHAR(50) NOT NULL,
    country            VARCHAR(5) NOT NULL,
    credit_rating      VARCHAR(5) NOT NULL,
    total_assets       NUMERIC(18, 2),
    total_liabilities  NUMERIC(18, 2),
    equity             NUMERIC(18, 2),
    revenue            NUMERIC(18, 2),
    net_income         NUMERIC(18, 2),
    interest_expense   NUMERIC(18, 2),
    current_assets     NUMERIC(18, 2),
    current_liabilities NUMERIC(18, 2),
    inventory          NUMERIC(18, 2),
    updated_at         TIMESTAMP DEFAULT NOW()
);

ALTER TABLE counterparties REPLICA IDENTITY FULL;

INSERT INTO counterparties VALUES
('CP001', 'Meridian Capital Partners', 'FINANCIALS', 'US', 'AA', 5000000.00, 2000000.00, 3000000.00, 1200000.00, 350000.00, 80000.00, 2500000.00, 1000000.00, 100000.00, NOW()),
('CP002', 'Atlas Industrial Holdings', 'INDUSTRIALS', 'GB', 'A', 8000000.00, 4500000.00, 3500000.00, 2500000.00, 600000.00, 150000.00, 3000000.00, 1800000.00, 500000.00, NOW()),
('CP003', 'Nexus Technology Corp', 'TECHNOLOGY', 'US', 'BBB', 3000000.00, 1500000.00, 1500000.00, 900000.00, 200000.00, 40000.00, 1800000.00, 700000.00, 50000.00, NOW()),
('CP004', 'Pacific Energy Solutions', 'ENERGY', 'AU', 'A', 12000000.00, 7000000.00, 5000000.00, 4000000.00, 800000.00, 300000.00, 4000000.00, 2500000.00, 200000.00, NOW()),
('CP005', 'Nordic Healthcare Group', 'HEALTHCARE', 'SE', 'AA', 6000000.00, 2500000.00, 3500000.00, 1800000.00, 450000.00, 60000.00, 3200000.00, 1200000.00, 300000.00, NOW()),
('CP006', 'Continental Logistics AG', 'INDUSTRIALS', 'DE', 'BBB', 4000000.00, 2800000.00, 1200000.00, 1500000.00, 150000.00, 120000.00, 1500000.00, 1100000.00, 400000.00, NOW()),
('CP007', 'Apex Financial Services', 'FINANCIALS', 'US', 'A', 15000000.00, 10000000.00, 5000000.00, 3000000.00, 700000.00, 400000.00, 6000000.00, 4000000.00, 0.00, NOW()),
('CP008', 'Solaris Renewable Energy', 'ENERGY', 'ES', 'BB', 2000000.00, 1600000.00, 400000.00, 500000.00, -50000.00, 100000.00, 600000.00, 500000.00, 50000.00, NOW()),
('CP009', 'Quantum Computing Labs', 'TECHNOLOGY', 'US', 'B', 800000.00, 600000.00, 200000.00, 150000.00, -100000.00, 30000.00, 400000.00, 350000.00, 10000.00, NOW()),
('CP010', 'Heritage Consumer Brands', 'CONSUMER', 'GB', 'A', 7000000.00, 3000000.00, 4000000.00, 2200000.00, 500000.00, 90000.00, 3500000.00, 1500000.00, 800000.00, NOW()),
('CP011', 'Titan Mining Corporation', 'MATERIALS', 'CA', 'BBB', 9000000.00, 5500000.00, 3500000.00, 3000000.00, 400000.00, 250000.00, 2800000.00, 2000000.00, 600000.00, NOW()),
('CP012', 'Azure Telecom Networks', 'TELECOM', 'JP', 'AA', 20000000.00, 11000000.00, 9000000.00, 6000000.00, 1200000.00, 500000.00, 5000000.00, 3000000.00, 100000.00, NOW()),
('CP013', 'Emerald Pharmaceuticals', 'HEALTHCARE', 'CH', 'A', 4500000.00, 1800000.00, 2700000.00, 1300000.00, 350000.00, 50000.00, 2200000.00, 800000.00, 200000.00, NOW()),
('CP014', 'Sterling Real Estate Trust', 'REAL_ESTATE', 'US', 'BBB', 25000000.00, 18000000.00, 7000000.00, 2000000.00, 300000.00, 900000.00, 1500000.00, 1200000.00, 0.00, NOW()),
('CP015', 'Vanguard Defense Systems', 'INDUSTRIALS', 'US', 'A', 11000000.00, 5000000.00, 6000000.00, 3500000.00, 800000.00, 200000.00, 4500000.00, 2000000.00, 300000.00, NOW()),
('CP016', 'Coral Insurance Group', 'FINANCIALS', 'BM', 'AA', 30000000.00, 25000000.00, 5000000.00, 4000000.00, 600000.00, 100000.00, 8000000.00, 6000000.00, 0.00, NOW()),
('CP017', 'Redwood Biotech', 'HEALTHCARE', 'US', 'BB', 1500000.00, 1000000.00, 500000.00, 300000.00, -200000.00, 60000.00, 700000.00, 400000.00, 100000.00, NOW()),
('CP018', 'Pinnacle Automotive', 'CONSUMER', 'DE', 'A', 18000000.00, 10000000.00, 8000000.00, 8000000.00, 1000000.00, 350000.00, 7000000.00, 4000000.00, 2000000.00, NOW()),
('CP019', 'Cascade Utilities', 'UTILITIES', 'US', 'AA', 14000000.00, 8000000.00, 6000000.00, 3000000.00, 500000.00, 400000.00, 2000000.00, 1500000.00, 50000.00, NOW()),
('CP020', 'Nova Semiconductor', 'TECHNOLOGY', 'TW', 'A', 10000000.00, 4000000.00, 6000000.00, 5000000.00, 1500000.00, 100000.00, 5500000.00, 2000000.00, 800000.00, NOW())
ON CONFLICT (counterparty_id) DO NOTHING;

-- ============================================================
-- Transactions
-- ============================================================

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id    VARCHAR(20) PRIMARY KEY,
    counterparty_id   VARCHAR(10) NOT NULL,
    direction         VARCHAR(4) NOT NULL,
    instrument_id     VARCHAR(20) NOT NULL,
    instrument_type   VARCHAR(20) NOT NULL,
    amount            NUMERIC(18, 2) NOT NULL,
    currency          VARCHAR(3) NOT NULL,
    transaction_date  DATE NOT NULL,
    quantity          INTEGER NOT NULL,
    updated_at        TIMESTAMP DEFAULT NOW()
);

ALTER TABLE transactions REPLICA IDENTITY FULL;

-- Generate ~900 transactions across counterparties and instruments
-- Using a series-based approach for reproducible seed data

INSERT INTO transactions
SELECT
    'TXN' || LPAD(s.id::text, 6, '0'),
    'CP' || LPAD((((s.id - 1) % 20) + 1)::text, 3, '0'),
    CASE WHEN s.id % 3 = 0 THEN 'SELL' ELSE 'BUY' END,
    (ARRAY['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'JPM', 'GS', 'BAC',
           'XOM', 'CVX', 'JNJ', 'PFE', 'UNH', 'T', 'VZ',
           'US10Y', 'US30Y', 'DE10Y', 'GB10Y', 'JP10Y',
           'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD',
           'SPX_C4500', 'SPX_P4200', 'AAPL_C180', 'TSLA_P200'])[((s.id - 1) % 28) + 1],
    CASE
        WHEN ((s.id - 1) % 28) + 1 <= 15 THEN 'EQUITY'
        WHEN ((s.id - 1) % 28) + 1 <= 20 THEN 'BOND'
        WHEN ((s.id - 1) % 28) + 1 <= 24 THEN 'FX'
        ELSE 'DERIVATIVE'
    END,
    ROUND((100 + (s.id * 137 % 9900))::numeric * 100, 2),
    CASE
        WHEN ((s.id - 1) % 28) + 1 BETWEEN 21 AND 22 THEN 'EUR'
        WHEN ((s.id - 1) % 28) + 1 = 23 THEN 'JPY'
        WHEN ((s.id - 1) % 28) + 1 = 24 THEN 'AUD'
        ELSE 'USD'
    END,
    CURRENT_DATE - (s.id % 365),
    10 + (s.id * 31 % 990),
    NOW()
FROM generate_series(1, 900) AS s(id)
ON CONFLICT (transaction_id) DO NOTHING;

-- ============================================================
-- Market Prices
-- ============================================================

CREATE TABLE IF NOT EXISTS market_prices (
    instrument_id    VARCHAR(20) NOT NULL,
    trade_date       DATE NOT NULL,
    instrument_type  VARCHAR(20) NOT NULL,
    open_price       NUMERIC(18, 2),
    high_price       NUMERIC(18, 2),
    low_price        NUMERIC(18, 2),
    close_price      NUMERIC(18, 2),
    volume           BIGINT,
    currency         VARCHAR(3) NOT NULL,
    updated_at       TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (instrument_id, trade_date)
);

ALTER TABLE market_prices REPLICA IDENTITY FULL;

-- Generate ~3200 market prices (28 instruments x ~115 trading days)
INSERT INTO market_prices
SELECT
    instruments.id,
    CURRENT_DATE - d.day_offset,
    instruments.itype,
    ROUND((instruments.base_price * (0.95 + (0.1 * RANDOM())))::numeric, 2),
    ROUND((instruments.base_price * (1.0 + (0.05 * RANDOM())))::numeric, 2),
    ROUND((instruments.base_price * (0.90 + (0.05 * RANDOM())))::numeric, 2),
    ROUND((instruments.base_price * (0.93 + (0.14 * RANDOM())))::numeric, 2),
    (100000 + FLOOR(RANDOM() * 900000))::bigint,
    instruments.curr,
    NOW()
FROM (
    VALUES
        ('AAPL', 'EQUITY', 175.00, 'USD'), ('MSFT', 'EQUITY', 380.00, 'USD'),
        ('GOOGL', 'EQUITY', 140.00, 'USD'), ('AMZN', 'EQUITY', 155.00, 'USD'),
        ('TSLA', 'EQUITY', 240.00, 'USD'), ('JPM', 'EQUITY', 170.00, 'USD'),
        ('GS', 'EQUITY', 380.00, 'USD'), ('BAC', 'EQUITY', 32.00, 'USD'),
        ('XOM', 'EQUITY', 105.00, 'USD'), ('CVX', 'EQUITY', 150.00, 'USD'),
        ('JNJ', 'EQUITY', 155.00, 'USD'), ('PFE', 'EQUITY', 28.00, 'USD'),
        ('UNH', 'EQUITY', 520.00, 'USD'), ('T', 'EQUITY', 17.00, 'USD'),
        ('VZ', 'EQUITY', 35.00, 'USD'),
        ('US10Y', 'BOND', 96.50, 'USD'), ('US30Y', 'BOND', 94.00, 'USD'),
        ('DE10Y', 'BOND', 98.00, 'EUR'), ('GB10Y', 'BOND', 97.00, 'GBP'),
        ('JP10Y', 'BOND', 99.50, 'JPY'),
        ('EURUSD', 'FX', 1.09, 'EUR'), ('GBPUSD', 'FX', 1.27, 'GBP'),
        ('USDJPY', 'FX', 149.00, 'JPY'), ('AUDUSD', 'FX', 0.66, 'AUD'),
        ('SPX_C4500', 'DERIVATIVE', 85.00, 'USD'), ('SPX_P4200', 'DERIVATIVE', 45.00, 'USD'),
        ('AAPL_C180', 'DERIVATIVE', 12.00, 'USD'), ('TSLA_P200', 'DERIVATIVE', 18.00, 'USD')
) AS instruments(id, itype, base_price, curr)
CROSS JOIN generate_series(0, 114) AS d(day_offset)
WHERE EXTRACT(DOW FROM CURRENT_DATE - d.day_offset) NOT IN (0, 6)  -- Skip weekends
ON CONFLICT (instrument_id, trade_date) DO NOTHING;

-- ============================================================
-- Credit Ratings History
-- ============================================================

CREATE TABLE IF NOT EXISTS credit_ratings_history (
    rating_id         VARCHAR(20) PRIMARY KEY,
    counterparty_id   VARCHAR(10) NOT NULL,
    rating_agency     VARCHAR(20) NOT NULL,
    rating            VARCHAR(10) NOT NULL,
    outlook           VARCHAR(20) NOT NULL,
    effective_date    DATE NOT NULL,
    previous_rating   VARCHAR(10),
    updated_at        TIMESTAMP DEFAULT NOW()
);

ALTER TABLE credit_ratings_history REPLICA IDENTITY FULL;

INSERT INTO credit_ratings_history VALUES
-- S&P ratings (20 counterparties)
('CRH001', 'CP001', 'S&P', 'AA', 'STABLE', '2025-01-15', 'AA-', NOW()),
('CRH002', 'CP002', 'S&P', 'A', 'POSITIVE', '2025-02-10', 'A-', NOW()),
('CRH003', 'CP003', 'S&P', 'BBB', 'STABLE', '2024-11-20', 'BBB', NOW()),
('CRH004', 'CP004', 'S&P', 'A', 'STABLE', '2025-01-05', 'A', NOW()),
('CRH005', 'CP005', 'S&P', 'AA', 'POSITIVE', '2024-12-01', 'AA-', NOW()),
('CRH006', 'CP006', 'S&P', 'BBB', 'NEGATIVE', '2025-03-01', 'BBB+', NOW()),
('CRH007', 'CP007', 'S&P', 'A', 'STABLE', '2024-10-15', 'A', NOW()),
('CRH008', 'CP008', 'S&P', 'BB', 'NEGATIVE', '2025-02-20', 'BB+', NOW()),
('CRH009', 'CP009', 'S&P', 'B', 'WATCH', '2025-03-10', 'B+', NOW()),
('CRH010', 'CP010', 'S&P', 'A', 'STABLE', '2024-09-15', 'A', NOW()),
('CRH011', 'CP011', 'S&P', 'BBB', 'STABLE', '2024-12-20', 'BBB-', NOW()),
('CRH012', 'CP012', 'S&P', 'AA', 'STABLE', '2025-01-25', 'AA', NOW()),
('CRH013', 'CP013', 'S&P', 'A', 'POSITIVE', '2024-11-10', 'A-', NOW()),
('CRH014', 'CP014', 'S&P', 'BBB', 'NEGATIVE', '2025-02-05', 'BBB', NOW()),
('CRH015', 'CP015', 'S&P', 'A', 'STABLE', '2024-10-01', 'A', NOW()),
('CRH016', 'CP016', 'S&P', 'AA', 'STABLE', '2025-01-10', 'AA', NOW()),
('CRH017', 'CP017', 'S&P', 'BB', 'WATCH', '2025-03-05', 'BB', NOW()),
('CRH018', 'CP018', 'S&P', 'A', 'STABLE', '2024-12-15', 'A', NOW()),
('CRH019', 'CP019', 'S&P', 'AA', 'POSITIVE', '2025-02-01', 'AA-', NOW()),
('CRH020', 'CP020', 'S&P', 'A', 'STABLE', '2024-11-05', 'A', NOW()),

-- Moody's ratings (20 counterparties)
('CRH021', 'CP001', 'MOODY''S', 'Aa2', 'STABLE', '2025-01-20', 'Aa3', NOW()),
('CRH022', 'CP002', 'MOODY''S', 'A2', 'POSITIVE', '2025-02-15', 'A3', NOW()),
('CRH023', 'CP003', 'MOODY''S', 'Baa2', 'STABLE', '2024-11-25', 'Baa2', NOW()),
('CRH024', 'CP004', 'MOODY''S', 'A2', 'STABLE', '2025-01-10', 'A2', NOW()),
('CRH025', 'CP005', 'MOODY''S', 'Aa2', 'POSITIVE', '2024-12-05', 'Aa3', NOW()),
('CRH026', 'CP006', 'MOODY''S', 'Baa2', 'NEGATIVE', '2025-03-05', 'Baa1', NOW()),
('CRH027', 'CP007', 'MOODY''S', 'A2', 'STABLE', '2024-10-20', 'A2', NOW()),
('CRH028', 'CP008', 'MOODY''S', 'Ba2', 'NEGATIVE', '2025-02-25', 'Ba1', NOW()),
('CRH029', 'CP009', 'MOODY''S', 'B2', 'WATCH', '2025-03-15', 'B1', NOW()),
('CRH030', 'CP010', 'MOODY''S', 'A2', 'STABLE', '2024-09-20', 'A2', NOW()),
('CRH031', 'CP011', 'MOODY''S', 'Baa2', 'STABLE', '2024-12-25', 'Baa3', NOW()),
('CRH032', 'CP012', 'MOODY''S', 'Aa2', 'STABLE', '2025-01-30', 'Aa2', NOW()),
('CRH033', 'CP013', 'MOODY''S', 'A2', 'POSITIVE', '2024-11-15', 'A3', NOW()),
('CRH034', 'CP014', 'MOODY''S', 'Baa2', 'NEGATIVE', '2025-02-10', 'Baa2', NOW()),
('CRH035', 'CP015', 'MOODY''S', 'A2', 'STABLE', '2024-10-05', 'A2', NOW()),
('CRH036', 'CP016', 'MOODY''S', 'Aa2', 'STABLE', '2025-01-15', 'Aa2', NOW()),
('CRH037', 'CP017', 'MOODY''S', 'Ba2', 'WATCH', '2025-03-10', 'Ba2', NOW()),
('CRH038', 'CP018', 'MOODY''S', 'A2', 'STABLE', '2024-12-20', 'A2', NOW()),
('CRH039', 'CP019', 'MOODY''S', 'Aa2', 'POSITIVE', '2025-02-05', 'Aa3', NOW()),
('CRH040', 'CP020', 'MOODY''S', 'A2', 'STABLE', '2024-11-10', 'A2', NOW()),

-- Fitch ratings (20 counterparties)
('CRH041', 'CP001', 'FITCH', 'AA', 'STABLE', '2025-01-18', 'AA-', NOW()),
('CRH042', 'CP002', 'FITCH', 'A', 'POSITIVE', '2025-02-12', 'A-', NOW()),
('CRH043', 'CP003', 'FITCH', 'BBB', 'STABLE', '2024-11-22', 'BBB', NOW()),
('CRH044', 'CP004', 'FITCH', 'A', 'STABLE', '2025-01-08', 'A', NOW()),
('CRH045', 'CP005', 'FITCH', 'AA', 'POSITIVE', '2024-12-03', 'AA-', NOW()),
('CRH046', 'CP006', 'FITCH', 'BBB', 'NEGATIVE', '2025-03-03', 'BBB+', NOW()),
('CRH047', 'CP007', 'FITCH', 'A', 'STABLE', '2024-10-18', 'A', NOW()),
('CRH048', 'CP008', 'FITCH', 'BB', 'NEGATIVE', '2025-02-22', 'BB+', NOW()),
('CRH049', 'CP009', 'FITCH', 'B', 'WATCH', '2025-03-12', 'B+', NOW()),
('CRH050', 'CP010', 'FITCH', 'A', 'STABLE', '2024-09-18', 'A', NOW()),
('CRH051', 'CP011', 'FITCH', 'BBB', 'STABLE', '2024-12-22', 'BBB-', NOW()),
('CRH052', 'CP012', 'FITCH', 'AA', 'STABLE', '2025-01-28', 'AA', NOW()),
('CRH053', 'CP013', 'FITCH', 'A', 'POSITIVE', '2024-11-12', 'A-', NOW()),
('CRH054', 'CP014', 'FITCH', 'BBB', 'NEGATIVE', '2025-02-08', 'BBB', NOW()),
('CRH055', 'CP015', 'FITCH', 'A', 'STABLE', '2024-10-03', 'A', NOW()),
('CRH056', 'CP016', 'FITCH', 'AA', 'STABLE', '2025-01-12', 'AA', NOW()),
('CRH057', 'CP017', 'FITCH', 'BB', 'WATCH', '2025-03-08', 'BB', NOW()),
('CRH058', 'CP018', 'FITCH', 'A', 'STABLE', '2024-12-18', 'A', NOW()),
('CRH059', 'CP019', 'FITCH', 'AA', 'POSITIVE', '2025-02-03', 'AA-', NOW()),
('CRH060', 'CP020', 'FITCH', 'A', 'STABLE', '2024-11-08', 'A', NOW())
ON CONFLICT (rating_id) DO NOTHING;

-- ============================================================
-- Office Locations
-- ============================================================

CREATE TABLE IF NOT EXISTS office_locations (
    office_id    VARCHAR(10) PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    city         VARCHAR(50) NOT NULL,
    country      VARCHAR(5) NOT NULL,
    region       VARCHAR(20) NOT NULL,
    timezone     VARCHAR(50) NOT NULL,
    is_active    BOOLEAN DEFAULT TRUE,
    updated_at   TIMESTAMP DEFAULT NOW()
);

ALTER TABLE office_locations REPLICA IDENTITY FULL;

INSERT INTO office_locations VALUES
('OFF001', 'New York HQ', 'New York', 'US', 'AMERICAS', 'America/New_York', TRUE, NOW()),
('OFF002', 'London Office', 'London', 'GB', 'EMEA', 'Europe/London', TRUE, NOW()),
('OFF003', 'Tokyo Office', 'Tokyo', 'JP', 'APAC', 'Asia/Tokyo', TRUE, NOW()),
('OFF004', 'Singapore Office', 'Singapore', 'SG', 'APAC', 'Asia/Singapore', TRUE, NOW()),
('OFF005', 'Frankfurt Office', 'Frankfurt', 'DE', 'EMEA', 'Europe/Berlin', TRUE, NOW()),
('OFF006', 'Hong Kong Office', 'Hong Kong', 'HK', 'APAC', 'Asia/Hong_Kong', TRUE, NOW()),
('OFF007', 'Chicago Office', 'Chicago', 'US', 'AMERICAS', 'America/Chicago', TRUE, NOW()),
('OFF008', 'Sydney Office', 'Sydney', 'AU', 'APAC', 'Australia/Sydney', FALSE, NOW())
ON CONFLICT (office_id) DO NOTHING;

-- ============================================================
-- Trading Desks
-- ============================================================

CREATE TABLE IF NOT EXISTS trading_desks (
    desk_id      VARCHAR(10) PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    office_id    VARCHAR(10) NOT NULL,
    asset_class  VARCHAR(30) NOT NULL,
    head_trader  VARCHAR(100) NOT NULL,
    is_active    BOOLEAN DEFAULT TRUE,
    updated_at   TIMESTAMP DEFAULT NOW()
);

ALTER TABLE trading_desks REPLICA IDENTITY FULL;

INSERT INTO trading_desks VALUES
('DSK001', 'Equities — New York', 'OFF001', 'EQUITIES', 'James Mitchell', TRUE, NOW()),
('DSK002', 'Fixed Income — New York', 'OFF001', 'FIXED_INCOME', 'Sarah Chen', TRUE, NOW()),
('DSK003', 'FX — London', 'OFF002', 'FX', 'Oliver Williams', TRUE, NOW()),
('DSK004', 'Derivatives — London', 'OFF002', 'DERIVATIVES', 'Emma Thompson', TRUE, NOW()),
('DSK005', 'Equities — Tokyo', 'OFF003', 'EQUITIES', 'Takeshi Yamamoto', TRUE, NOW()),
('DSK006', 'FX — Singapore', 'OFF004', 'FX', 'Wei Lin Tan', TRUE, NOW()),
('DSK007', 'Fixed Income — Frankfurt', 'OFF005', 'FIXED_INCOME', 'Hans Mueller', TRUE, NOW()),
('DSK008', 'Derivatives — Hong Kong', 'OFF006', 'DERIVATIVES', 'Li Wei Zhang', TRUE, NOW()),
('DSK009', 'Equities — London', 'OFF002', 'EQUITIES', 'Andrew Blackwood', TRUE, NOW()),
('DSK010', 'FX — New York', 'OFF001', 'FX', 'Maria Rodriguez', TRUE, NOW()),
('DSK011', 'Fixed Income — Tokyo', 'OFF003', 'FIXED_INCOME', 'Kenji Nakamura', TRUE, NOW()),
('DSK012', 'Derivatives — Chicago', 'OFF007', 'DERIVATIVES', 'Robert Johnson', TRUE, NOW())
ON CONFLICT (desk_id) DO NOTHING;

-- ============================================================
-- Desk Assignments
-- ============================================================

CREATE TABLE IF NOT EXISTS desk_assignments (
    assignment_id   VARCHAR(20) PRIMARY KEY,
    desk_id         VARCHAR(10) NOT NULL,
    counterparty_id VARCHAR(10) NOT NULL,
    instrument_type VARCHAR(20) NOT NULL,
    effective_date  DATE NOT NULL,
    end_date        DATE,
    updated_at      TIMESTAMP DEFAULT NOW()
);

ALTER TABLE desk_assignments REPLICA IDENTITY FULL;

INSERT INTO desk_assignments VALUES
-- Equities NY (DSK001)
('ASG001', 'DSK001', 'CP001', 'EQUITY', '2024-01-01', NULL, NOW()),
('ASG002', 'DSK001', 'CP003', 'EQUITY', '2024-01-01', NULL, NOW()),
('ASG003', 'DSK001', 'CP007', 'EQUITY', '2024-01-01', NULL, NOW()),
('ASG004', 'DSK001', 'CP010', 'EQUITY', '2024-03-15', NULL, NOW()),
-- Fixed Income NY (DSK002)
('ASG005', 'DSK002', 'CP001', 'BOND', '2024-01-01', NULL, NOW()),
('ASG006', 'DSK002', 'CP004', 'BOND', '2024-01-01', NULL, NOW()),
('ASG007', 'DSK002', 'CP014', 'BOND', '2024-02-01', NULL, NOW()),
('ASG008', 'DSK002', 'CP019', 'BOND', '2024-01-01', NULL, NOW()),
-- FX London (DSK003)
('ASG009', 'DSK003', 'CP002', 'FX', '2024-01-01', NULL, NOW()),
('ASG010', 'DSK003', 'CP006', 'FX', '2024-01-01', NULL, NOW()),
('ASG011', 'DSK003', 'CP010', 'FX', '2024-04-01', NULL, NOW()),
-- Derivatives London (DSK004)
('ASG012', 'DSK004', 'CP002', 'DERIVATIVE', '2024-01-01', NULL, NOW()),
('ASG013', 'DSK004', 'CP005', 'DERIVATIVE', '2024-01-01', NULL, NOW()),
('ASG014', 'DSK004', 'CP008', 'DERIVATIVE', '2024-02-15', NULL, NOW()),
-- Equities Tokyo (DSK005)
('ASG015', 'DSK005', 'CP012', 'EQUITY', '2024-01-01', NULL, NOW()),
('ASG016', 'DSK005', 'CP020', 'EQUITY', '2024-01-01', NULL, NOW()),
('ASG017', 'DSK005', 'CP018', 'EQUITY', '2024-05-01', NULL, NOW()),
-- FX Singapore (DSK006)
('ASG018', 'DSK006', 'CP004', 'FX', '2024-01-01', NULL, NOW()),
('ASG019', 'DSK006', 'CP012', 'FX', '2024-01-01', NULL, NOW()),
('ASG020', 'DSK006', 'CP020', 'FX', '2024-03-01', NULL, NOW()),
-- Fixed Income Frankfurt (DSK007)
('ASG021', 'DSK007', 'CP006', 'BOND', '2024-01-01', NULL, NOW()),
('ASG022', 'DSK007', 'CP013', 'BOND', '2024-01-01', NULL, NOW()),
('ASG023', 'DSK007', 'CP018', 'BOND', '2024-02-01', NULL, NOW()),
-- Derivatives HK (DSK008)
('ASG024', 'DSK008', 'CP012', 'DERIVATIVE', '2024-01-01', NULL, NOW()),
('ASG025', 'DSK008', 'CP020', 'DERIVATIVE', '2024-01-01', NULL, NOW()),
('ASG026', 'DSK008', 'CP004', 'DERIVATIVE', '2024-04-01', NULL, NOW()),
-- Equities London (DSK009)
('ASG027', 'DSK009', 'CP002', 'EQUITY', '2024-01-01', NULL, NOW()),
('ASG028', 'DSK009', 'CP005', 'EQUITY', '2024-01-01', NULL, NOW()),
('ASG029', 'DSK009', 'CP013', 'EQUITY', '2024-03-15', NULL, NOW()),
-- FX NY (DSK010)
('ASG030', 'DSK010', 'CP001', 'FX', '2024-01-01', NULL, NOW()),
('ASG031', 'DSK010', 'CP007', 'FX', '2024-01-01', NULL, NOW()),
('ASG032', 'DSK010', 'CP015', 'FX', '2024-02-01', NULL, NOW()),
-- Fixed Income Tokyo (DSK011)
('ASG033', 'DSK011', 'CP012', 'BOND', '2024-01-01', NULL, NOW()),
('ASG034', 'DSK011', 'CP020', 'BOND', '2024-01-01', NULL, NOW()),
-- Derivatives Chicago (DSK012)
('ASG035', 'DSK012', 'CP009', 'DERIVATIVE', '2024-01-01', NULL, NOW()),
('ASG036', 'DSK012', 'CP017', 'DERIVATIVE', '2024-01-01', NULL, NOW()),
('ASG037', 'DSK012', 'CP003', 'DERIVATIVE', '2024-06-01', NULL, NOW()),
-- Historical (ended) assignments
('ASG038', 'DSK001', 'CP009', 'EQUITY', '2023-06-01', '2024-01-15', NOW()),
('ASG039', 'DSK003', 'CP008', 'FX', '2023-01-01', '2024-03-01', NOW()),
('ASG040', 'DSK005', 'CP016', 'EQUITY', '2023-09-01', '2024-06-30', NOW())
ON CONFLICT (assignment_id) DO NOTHING;

COMMIT;
