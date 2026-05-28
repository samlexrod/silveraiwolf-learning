"""Synthetic financial data for Gold table seeding.

Contains realistic counterparty risk, financial ratio, and portfolio
summary data used by create_gold_tables.py to populate the Gold layer.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Risk Exposure data — counterparty-level risk metrics
# ---------------------------------------------------------------------------

RISK_EXPOSURE_DATA = [
    {
        "counterparty_name": "Acme Corp",
        "risk_tier": "HIGH",
        "total_exposure_usd": 2500000.00,
        "credit_rating": "BB+",
        "default_probability": 0.042,
        "sector": "Manufacturing",
        "country": "US",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "GlobalTech Inc",
        "risk_tier": "MEDIUM",
        "total_exposure_usd": 4200000.00,
        "credit_rating": "BBB",
        "default_probability": 0.018,
        "sector": "Technology",
        "country": "US",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Meridian Bank",
        "risk_tier": "LOW",
        "total_exposure_usd": 1200000.00,
        "credit_rating": "A+",
        "default_probability": 0.003,
        "sector": "Financial Services",
        "country": "UK",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Vertex Capital",
        "risk_tier": "HIGH",
        "total_exposure_usd": 3900000.00,
        "credit_rating": "BB-",
        "default_probability": 0.058,
        "sector": "Financial Services",
        "country": "US",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Oceanic Trading",
        "risk_tier": "CRITICAL",
        "total_exposure_usd": 8200000.00,
        "credit_rating": "B",
        "default_probability": 0.125,
        "sector": "Energy",
        "country": "SG",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Pinnacle Industries",
        "risk_tier": "CRITICAL",
        "total_exposure_usd": 5100000.00,
        "credit_rating": "B+",
        "default_probability": 0.098,
        "sector": "Manufacturing",
        "country": "DE",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Zenith Energy",
        "risk_tier": "HIGH",
        "total_exposure_usd": 4500000.00,
        "credit_rating": "BB",
        "default_probability": 0.065,
        "sector": "Energy",
        "country": "US",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Cascade Health",
        "risk_tier": "LOW",
        "total_exposure_usd": 1800000.00,
        "credit_rating": "A",
        "default_probability": 0.005,
        "sector": "Healthcare",
        "country": "US",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Nordic Finance",
        "risk_tier": "LOW",
        "total_exposure_usd": 2100000.00,
        "credit_rating": "AA-",
        "default_probability": 0.002,
        "sector": "Financial Services",
        "country": "NO",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Atlas Semiconductor",
        "risk_tier": "MEDIUM",
        "total_exposure_usd": 3600000.00,
        "credit_rating": "BBB+",
        "default_probability": 0.015,
        "sector": "Technology",
        "country": "TW",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "SilverLine Pharma",
        "risk_tier": "LOW",
        "total_exposure_usd": 1400000.00,
        "credit_rating": "A-",
        "default_probability": 0.007,
        "sector": "Healthcare",
        "country": "CH",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Redwood Capital",
        "risk_tier": "MEDIUM",
        "total_exposure_usd": 2800000.00,
        "credit_rating": "BBB-",
        "default_probability": 0.025,
        "sector": "Financial Services",
        "country": "US",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Horizon Dynamics",
        "risk_tier": "MEDIUM",
        "total_exposure_usd": 2200000.00,
        "credit_rating": "BBB",
        "default_probability": 0.020,
        "sector": "Technology",
        "country": "JP",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Quantum Networks",
        "risk_tier": "HIGH",
        "total_exposure_usd": 2400000.00,
        "credit_rating": "BB",
        "default_probability": 0.048,
        "sector": "Technology",
        "country": "US",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Pacific Petroleum",
        "risk_tier": "MEDIUM",
        "total_exposure_usd": 2500000.00,
        "credit_rating": "BBB",
        "default_probability": 0.022,
        "sector": "Energy",
        "country": "AU",
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Summit Financial",
        "risk_tier": "LOW",
        "total_exposure_usd": 1600000.00,
        "credit_rating": "A",
        "default_probability": 0.004,
        "sector": "Financial Services",
        "country": "CA",
        "last_updated": "2025-03-15",
    },
]


# ---------------------------------------------------------------------------
# Financial Ratios data — key financial health indicators
# ---------------------------------------------------------------------------

FINANCIAL_RATIOS_DATA = [
    {
        "counterparty_name": "Acme Corp",
        "debt_to_equity": 2.15,
        "current_ratio": 1.05,
        "interest_coverage": 2.8,
        "return_on_equity": 0.065,
        "revenue_growth_pct": -1.2,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "GlobalTech Inc",
        "debt_to_equity": 1.85,
        "current_ratio": 1.20,
        "interest_coverage": 3.4,
        "return_on_equity": 0.085,
        "revenue_growth_pct": -2.1,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Meridian Bank",
        "debt_to_equity": 0.45,
        "current_ratio": 2.80,
        "interest_coverage": 12.5,
        "return_on_equity": 0.142,
        "revenue_growth_pct": 5.8,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Vertex Capital",
        "debt_to_equity": 2.90,
        "current_ratio": 0.88,
        "interest_coverage": 1.5,
        "return_on_equity": 0.035,
        "revenue_growth_pct": -4.5,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Oceanic Trading",
        "debt_to_equity": 4.20,
        "current_ratio": 0.72,
        "interest_coverage": 0.9,
        "return_on_equity": -0.025,
        "revenue_growth_pct": -12.3,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Pinnacle Industries",
        "debt_to_equity": 3.65,
        "current_ratio": 0.80,
        "interest_coverage": 1.2,
        "return_on_equity": 0.012,
        "revenue_growth_pct": -8.7,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Zenith Energy",
        "debt_to_equity": 3.42,
        "current_ratio": 0.95,
        "interest_coverage": 1.8,
        "return_on_equity": 0.032,
        "revenue_growth_pct": -5.3,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Cascade Health",
        "debt_to_equity": 0.60,
        "current_ratio": 2.50,
        "interest_coverage": 10.2,
        "return_on_equity": 0.125,
        "revenue_growth_pct": 8.4,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Nordic Finance",
        "debt_to_equity": 0.30,
        "current_ratio": 3.10,
        "interest_coverage": 15.8,
        "return_on_equity": 0.168,
        "revenue_growth_pct": 6.2,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Atlas Semiconductor",
        "debt_to_equity": 1.20,
        "current_ratio": 1.65,
        "interest_coverage": 5.2,
        "return_on_equity": 0.098,
        "revenue_growth_pct": 3.1,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "SilverLine Pharma",
        "debt_to_equity": 0.55,
        "current_ratio": 2.35,
        "interest_coverage": 9.8,
        "return_on_equity": 0.112,
        "revenue_growth_pct": 7.6,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Redwood Capital",
        "debt_to_equity": 1.75,
        "current_ratio": 1.15,
        "interest_coverage": 3.1,
        "return_on_equity": 0.072,
        "revenue_growth_pct": 0.5,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Horizon Dynamics",
        "debt_to_equity": 1.40,
        "current_ratio": 1.45,
        "interest_coverage": 4.5,
        "return_on_equity": 0.091,
        "revenue_growth_pct": 2.3,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Quantum Networks",
        "debt_to_equity": 2.50,
        "current_ratio": 0.98,
        "interest_coverage": 2.1,
        "return_on_equity": 0.045,
        "revenue_growth_pct": -3.2,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Pacific Petroleum",
        "debt_to_equity": 1.60,
        "current_ratio": 1.30,
        "interest_coverage": 4.0,
        "return_on_equity": 0.078,
        "revenue_growth_pct": 1.8,
        "last_updated": "2025-03-15",
    },
    {
        "counterparty_name": "Summit Financial",
        "debt_to_equity": 0.40,
        "current_ratio": 2.90,
        "interest_coverage": 14.2,
        "return_on_equity": 0.155,
        "revenue_growth_pct": 4.9,
        "last_updated": "2025-03-15",
    },
]


# ---------------------------------------------------------------------------
# Portfolio Summary data — sector-level aggregates
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Portfolio definitions — named portfolios with strategy and manager
# ---------------------------------------------------------------------------

PORTFOLIOS_DATA = [
    {
        "portfolio_id": "PF-ALPHA",
        "portfolio_name": "Alpha Growth",
        "strategy": "Aggressive",
        "manager": "Sarah Chen",
        "created_date": "2024-01-15",
    },
    {
        "portfolio_id": "PF-MERID",
        "portfolio_name": "Meridian Income",
        "strategy": "Conservative",
        "manager": "James OBrien",
        "created_date": "2024-03-01",
    },
    {
        "portfolio_id": "PF-GLOBE",
        "portfolio_name": "Global Balanced",
        "strategy": "Balanced",
        "manager": "Maria Santos",
        "created_date": "2024-06-10",
    },
    {
        "portfolio_id": "PF-EMRKT",
        "portfolio_name": "Emerging Markets",
        "strategy": "Growth",
        "manager": "Raj Patel",
        "created_date": "2024-09-20",
    },
]


# ---------------------------------------------------------------------------
# Portfolio holdings — which counterparties are in each portfolio
# A counterparty can appear in multiple portfolios with different allocations
# ---------------------------------------------------------------------------

PORTFOLIO_HOLDINGS_DATA = [
    # Alpha Growth — Aggressive: heavy Tech + Energy, high-risk names
    {"portfolio_id": "PF-ALPHA", "counterparty_name": "GlobalTech Inc", "allocation_pct": 18.0, "position_type": "LONG"},
    {"portfolio_id": "PF-ALPHA", "counterparty_name": "Atlas Semiconductor", "allocation_pct": 15.0, "position_type": "LONG"},
    {"portfolio_id": "PF-ALPHA", "counterparty_name": "Quantum Networks", "allocation_pct": 12.0, "position_type": "LONG"},
    {"portfolio_id": "PF-ALPHA", "counterparty_name": "Oceanic Trading", "allocation_pct": 20.0, "position_type": "LONG"},
    {"portfolio_id": "PF-ALPHA", "counterparty_name": "Zenith Energy", "allocation_pct": 15.0, "position_type": "LONG"},
    {"portfolio_id": "PF-ALPHA", "counterparty_name": "Horizon Dynamics", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-ALPHA", "counterparty_name": "Pinnacle Industries", "allocation_pct": 10.0, "position_type": "LONG"},

    # Meridian Income — Conservative: Financial Services + Healthcare, low-risk
    {"portfolio_id": "PF-MERID", "counterparty_name": "Meridian Bank", "allocation_pct": 22.0, "position_type": "LONG"},
    {"portfolio_id": "PF-MERID", "counterparty_name": "Nordic Finance", "allocation_pct": 20.0, "position_type": "LONG"},
    {"portfolio_id": "PF-MERID", "counterparty_name": "Summit Financial", "allocation_pct": 18.0, "position_type": "LONG"},
    {"portfolio_id": "PF-MERID", "counterparty_name": "Cascade Health", "allocation_pct": 15.0, "position_type": "LONG"},
    {"portfolio_id": "PF-MERID", "counterparty_name": "SilverLine Pharma", "allocation_pct": 15.0, "position_type": "LONG"},
    {"portfolio_id": "PF-MERID", "counterparty_name": "Redwood Capital", "allocation_pct": 10.0, "position_type": "LONG"},

    # Global Balanced — Mixed across all sectors
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Meridian Bank", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "GlobalTech Inc", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Atlas Semiconductor", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Pacific Petroleum", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Cascade Health", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Nordic Finance", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Acme Corp", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Horizon Dynamics", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "Redwood Capital", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-GLOBE", "counterparty_name": "SilverLine Pharma", "allocation_pct": 10.0, "position_type": "LONG"},

    # Emerging Markets — Energy + Manufacturing, higher default risk
    {"portfolio_id": "PF-EMRKT", "counterparty_name": "Oceanic Trading", "allocation_pct": 25.0, "position_type": "LONG"},
    {"portfolio_id": "PF-EMRKT", "counterparty_name": "Pinnacle Industries", "allocation_pct": 20.0, "position_type": "LONG"},
    {"portfolio_id": "PF-EMRKT", "counterparty_name": "Zenith Energy", "allocation_pct": 20.0, "position_type": "LONG"},
    {"portfolio_id": "PF-EMRKT", "counterparty_name": "Pacific Petroleum", "allocation_pct": 15.0, "position_type": "LONG"},
    {"portfolio_id": "PF-EMRKT", "counterparty_name": "Acme Corp", "allocation_pct": 10.0, "position_type": "LONG"},
    {"portfolio_id": "PF-EMRKT", "counterparty_name": "Vertex Capital", "allocation_pct": 10.0, "position_type": "LONG"},
]


# ---------------------------------------------------------------------------
# Portfolio Summary data — sector-level aggregates (legacy, kept for backward compat)
# ---------------------------------------------------------------------------

PORTFOLIO_SUMMARY_DATA = [
    {
        "sector": "Technology",
        "num_counterparties": 4,
        "total_exposure_usd": 12400000.00,
        "concentration_pct": 32.5,
        "avg_risk_score": 6.2,
        "dominant_risk_tier": "MEDIUM",
    },
    {
        "sector": "Financial Services",
        "num_counterparties": 5,
        "total_exposure_usd": 10700000.00,
        "concentration_pct": 28.1,
        "avg_risk_score": 4.8,
        "dominant_risk_tier": "LOW",
    },
    {
        "sector": "Energy",
        "num_counterparties": 3,
        "total_exposure_usd": 15200000.00,
        "concentration_pct": 18.3,
        "avg_risk_score": 7.5,
        "dominant_risk_tier": "HIGH",
    },
    {
        "sector": "Manufacturing",
        "num_counterparties": 2,
        "total_exposure_usd": 7600000.00,
        "concentration_pct": 12.8,
        "avg_risk_score": 7.8,
        "dominant_risk_tier": "HIGH",
    },
    {
        "sector": "Healthcare",
        "num_counterparties": 2,
        "total_exposure_usd": 3200000.00,
        "concentration_pct": 8.3,
        "avg_risk_score": 2.5,
        "dominant_risk_tier": "LOW",
    },
]
