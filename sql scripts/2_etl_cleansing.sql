-- =========================================================================
-- STEP 1: POPULATE DIM_DRUG (Parsing arrays from staging)
-- =========================================================================

-- Pull clean drug names from staging recalls
INSERT INTO dim_drug (generic_name)
SELECT DISTINCT UPPER(regexp_replace("openfda.generic_name", '[{}"\[\]]', '', 'g'))
FROM stg_fda_recalls
WHERE "openfda.generic_name" IS NOT NULL AND "openfda.generic_name" != ''
ON CONFLICT (generic_name) DO NOTHING;

-- Pull clean drug names from staging events
INSERT INTO dim_drug (generic_name)
SELECT DISTINCT UPPER(regexp_replace("openfda.generic_name", '[{}"\[\]]', '', 'g'))
FROM stg_fda_events
WHERE "openfda.generic_name" IS NOT NULL AND "openfda.generic_name" != ''
ON CONFLICT (generic_name) DO NOTHING;

-- =========================================================================
-- STEP 2: POPULATE DIM_MANUFACTURER
-- =========================================================================
INSERT INTO dim_manufacturer (company_name)
SELECT DISTINCT UPPER(regexp_replace("openfda.manufacturer_name", '[{}"\[\]]', '', 'g'))
FROM stg_fda_recalls
WHERE "openfda.manufacturer_name" IS NOT NULL AND "openfda.manufacturer_name" != ''
ON CONFLICT (company_name) DO NOTHING;

-- =========================================================================
-- STEP 3: POPULATE CENTRAL FACT TABLE (Joining on clean lookups)
-- =========================================================================

-- Map and insert Recalls
INSERT INTO fact_regulatory_events (drug_id, mfg_id, event_date, event_type, source_reference, severity_score)
SELECT 
    d.drug_id,
    m.mfg_id,
    TO_DATE(r.report_date, 'YYYYMMDD'),
    'RECALL',
    r.recall_number,
    CASE WHEN r.classification = 'Class I' THEN 3 ELSE 2 END
FROM stg_fda_recalls r
JOIN dim_drug d ON d.generic_name = UPPER(regexp_replace(r."openfda.generic_name", '[{}"\[\]]', '', 'g'))
JOIN dim_manufacturer m ON m.company_name = UPPER(regexp_replace(r."openfda.manufacturer_name", '[{}"\[\]]', '', 'g'));

-- Map and insert Adverse Events
INSERT INTO fact_regulatory_events (drug_id, mfg_id, event_date, event_type, source_reference, severity_score)
SELECT 
    d.drug_id,
    NULL, -- Leave blank as events target patient drug consumption, not manufacturer lines
    TO_DATE(e.receivedate, 'YYYYMMDD'),
    'ADVERSE_EVENT',
    e.safetyreportid,
    1
FROM stg_fda_events e
JOIN dim_drug d ON d.generic_name = UPPER(regexp_replace(e."openfda.generic_name", '[{}"\[\]]', '', 'g'));