-- =========================================================================
-- STEP 1: DROP TABLES IF THEY ALREADY EXIST (For clean pipeline resets)
-- =========================================================================
DROP TABLE IF EXISTS high_risk_alerts;
DROP TABLE IF EXISTS fact_regulatory_events;
DROP TABLE IF EXISTS dim_manufacturer;
DROP TABLE IF EXISTS dim_drug;

-- =========================================================================
-- STEP 2: CREATE DIMENSION TABLES
-- =========================================================================

-- Drug Dimension: Keeps a unique list of generic drug strings
CREATE TABLE dim_drug (
    drug_id SERIAL PRIMARY KEY,
    generic_name VARCHAR(255) UNIQUE NOT NULL,
    therapeutic_class VARCHAR(255) NULL
);

-- Manufacturer Dimension: Tracks unique manufacturing firms
CREATE TABLE dim_manufacturer (
    mfg_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) UNIQUE NOT NULL
);

-- =========================================================================
-- STEP 3: CREATE FACT HUB TABLE
-- =========================================================================

-- Fact Regulatory Events: The central metrics table linking dimensions to dates
CREATE TABLE fact_regulatory_events (
    event_id SERIAL PRIMARY KEY,
    drug_id INT REFERENCES dim_drug(drug_id),
    mfg_id INT REFERENCES dim_manufacturer(mfg_id),
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'RECALL' or 'ADVERSE_EVENT'
    source_reference VARCHAR(100),   -- safetyreportid or recall_number
    severity_score INT DEFAULT 1     -- Class I = 3, Class II = 2, Adverse Event = 1
);

-- =========================================================================
-- STEP 4: CREATE ANOMALY STAGING TABLE
-- =========================================================================

-- High Risk Alerts: Holds the final statistical outputs from Python
CREATE TABLE high_risk_alerts (
    alert_id SERIAL PRIMARY KEY,
    generic_name VARCHAR(255),
    alert_month DATE,
    actual_event_count INT,
    historical_rolling_mean NUMERIC(10,2),
    z_score NUMERIC(10,2),
    alert_flag VARCHAR(50) DEFAULT 'HIGH_RISK'
);