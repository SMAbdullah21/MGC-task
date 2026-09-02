-- SQL Server schema for the historical CRM export.
--
-- One table is sufficient for this exercise: every CSV row describes one lead
-- record and the file contains no reusable agent/customer entity attributes.
-- NUMERIC(..., 1) is used for columns exported as values such as "1.0", allowing
-- the CSV to load directly without lossy text storage.

CREATE TABLE dbo.leads (
    lead_id                      NVARCHAR(16) NOT NULL,
    created_at                   DATETIME2(0) NOT NULL,
    source                       NVARCHAR(100) NOT NULL,
    city                         NVARCHAR(100) NOT NULL,
    area                         NVARCHAR(100) NULL,
    property_type                NVARCHAR(100) NOT NULL,
    budget_pkr_lac               DECIMAL(10, 1) NULL,
    bedrooms                     DECIMAL(2, 1) NULL,
    first_response_minutes       DECIMAL(10, 1) NULL,
    calls_made                   SMALLINT NOT NULL,
    total_call_seconds           DECIMAL(12, 1) NOT NULL,
    whatsapp_replies             SMALLINT NOT NULL,
    site_visits                  SMALLINT NOT NULL,
    agent_experience_years       DECIMAL(4, 1) NULL,
    is_overseas                  BIT NOT NULL,
    referred_by_existing_client BIT NOT NULL,
    has_financing_approved       BIT NOT NULL,
    token_amount_received_pkr    DECIMAL(15, 1) NOT NULL,
    crm_record_hash              BIGINT NOT NULL,
    converted                    BIT NOT NULL,

    CONSTRAINT PK_leads PRIMARY KEY (lead_id),
    CONSTRAINT CK_leads_calls_made CHECK (calls_made >= 0),
    CONSTRAINT CK_leads_total_call_seconds CHECK (total_call_seconds >= 0),
    CONSTRAINT CK_leads_whatsapp_replies CHECK (whatsapp_replies >= 0),
    CONSTRAINT CK_leads_site_visits CHECK (site_visits >= 0),
    CONSTRAINT CK_leads_token_amount CHECK (token_amount_received_pkr >= 0),
    CONSTRAINT CK_leads_budget CHECK (budget_pkr_lac IS NULL OR budget_pkr_lac >= 0),
    CONSTRAINT CK_leads_bedrooms CHECK (bedrooms IS NULL OR bedrooms >= 0),
    CONSTRAINT CK_leads_first_response CHECK (first_response_minutes IS NULL OR first_response_minutes >= 0),
    CONSTRAINT CK_leads_agent_experience CHECK (agent_experience_years IS NULL OR agent_experience_years >= 0)
);

-- Keep this non-unique for the initial dirty historical import so the duplicates
-- remain inspectable. After resolving them, replace it with the UNIQUE index shown
-- in queries.sql to reject the same CRM identity at write time.
CREATE INDEX IX_leads_crm_record_hash ON dbo.leads (crm_record_hash);
CREATE INDEX IX_leads_source ON dbo.leads (source);

-- Import leads.csv with the SSMS Import Data wizard after creating this table.
