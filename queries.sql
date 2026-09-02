-- SQL Server / T-SQL

-- 1. Conversion rate by source, best first, for sources with at least 200 leads.
-- The percentage is rounded for display; converted_count is included so the
-- result remains easy to audit.
SELECT
    source,
    COUNT_BIG(*) AS lead_count,
    SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) AS converted_count,
    CAST(
        100.0 * SUM(CASE WHEN converted = 1 THEN 1 ELSE 0 END) / COUNT(*)
        AS DECIMAL(6, 2)
    ) AS conversion_rate_pct
FROM dbo.leads
GROUP BY source
HAVING COUNT(*) >= 200
ORDER BY conversion_rate_pct DESC, lead_count DESC, source ASC;


-- 2. Return every row belonging to a duplicated CRM identity.
-- lead_id is unique even for duplicates (some duplicate IDs have a "-B" suffix),
-- while crm_record_hash repeats and is therefore the correct identity signal.
WITH duplicate_hashes AS (
    SELECT crm_record_hash
    FROM dbo.leads
    GROUP BY crm_record_hash
    HAVING COUNT(*) > 1
)
SELECT
    l.*,
    COUNT(*) OVER (PARTITION BY l.crm_record_hash) AS duplicate_group_size
FROM dbo.leads AS l
JOIN duplicate_hashes AS d USING (crm_record_hash)
ORDER BY l.crm_record_hash, l.created_at, l.lead_id;

-- The CSV contains no agent ID, so the responsible agents cannot be displayed.
-- After reviewing/merging the existing duplicates, prevent future duplicates at
-- schema level by replacing the ordinary hash index with a UNIQUE index:
--
-- DROP INDEX IX_leads_crm_record_hash ON dbo.leads;
-- CREATE UNIQUE INDEX UX_leads_crm_record_hash ON dbo.leads (crm_record_hash);
--
-- In production, import into a staging table first, then MERGE or INSERT only
-- hashes that do not already exist in dbo.leads.
