# MGC Task Pack

## Part 1: grounded document assistant

`assistant.py` is a dependency-free Gemini chatbot grounded in all Markdown files
under `docs/`. The documents are split into source chunks and supplied to Gemini.
Gemini must return a structured answer and the exact source IDs used; the CLI maps
those IDs back to filenames, sections, line numbers, and source text.

Set the API key in PowerShell (do not paste it into the code):

```powershell
$env:GEMINI_API_KEY = "your-new-gemini-api-key"
```

The default model is `gemini-3.6-flash`. Override it if needed:

```powershell
$env:GEMINI_MODEL = "gemini-3.6-flash"
```

Run one question:

```powershell
python assistant.py "What's the transfer fee?"
```

Or start interactive mode:

```powershell
python assistant.py
```

Keep that terminal open while running the assistant. Environment variables set this
way disappear when the terminal closes. Rotate any key that has been posted in chat.

Run the required behavior checks:

```powershell
python -m unittest -v
```

### Pricing interpretation

For the brief's phrase “2-bed Block B”, the assistant starts from the listed
**2-Bed Standard** base price and treats “corner” as the documented +3% location
premium. Thus floor 15 (+4%), corner (+3%), and Margalla-facing (+6%) add to +13%:
PKR 22,425,000 × 1.13 = **PKR 25,340,250**. Although the price list also has a
separate “2-Bed Corner” row, using that row and then adding the required +3% corner
premium would double-count “corner”. This interpretation follows the document's
own example that a floor-15 Margalla-facing corner unit adds 13% over base.

The five high-risk evaluation cases still use deterministic code for calculations,
conflict detection, and refusals. All other questions go to Gemini with the complete
small document corpus, so questions about amenities, approvals, booking, possession,
discounts, and policies are no longer limited to predefined intents.

## Part 2: database

The database solution uses Microsoft SQL Server and runs in SQL Server Management
Studio (SSMS):

- `schema.sql` defines one typed `leads` table with a primary key, nullability,
  named checks, and indexes.
- `queries.sql` contains the conversion-rate and duplicate-lead queries.

One table is intentional: the export contains lead facts but no agent identifier or
reusable customer/agent entity details worth normalizing. Profiling found 9,160 rows,
9,160 unique `lead_id` values, but only 9,000 unique `crm_record_hash` values. There
are 160 duplicate groups (320 rows), so duplicates are detected by
`crm_record_hash`, not by the superficially unique lead ID.

The initial schema keeps the hash index non-unique so the dirty historical data can
be loaded and investigated. After merging those duplicates, run the commented
`CREATE UNIQUE INDEX` in `queries.sql`; future imports should pass through a staging
table and reject hashes already present in `dbo.leads`.

### Run Part 2 in SSMS

1. Open SSMS and connect to your local SQL Server instance.
2. Right-click **Databases**, choose **New Database**, name it `mgc`, and select OK.
3. Select the `mgc` database in the SSMS database dropdown.
4. Open `schema.sql` with **File > Open > File**, then press **Execute**. This creates
   `dbo.leads` and its indexes.
5. Right-click the `mgc` database and choose **Tasks > Import Data** (not Import Flat
   File, which tries to create another table).
6. Choose **Flat File Source**, browse to `leads.csv`, enable **Column names in the
   first data row**, and verify comma-delimited format.
7. Choose your SQL Server instance as the destination and select the `mgc` database.
8. In **Select Source Tables and Views**, set the destination to `[dbo].[leads]`.
   Open **Edit Mappings**, confirm columns map by name and in the same order, then
   finish the import.
9. Confirm the import in a new query window:

```sql
USE mgc;
SELECT COUNT(*) AS imported_rows FROM dbo.leads;
```

The expected count is `9160`.

10. Open `queries.sql`, ensure `mgc` is selected in the database dropdown, and press
    **Execute**. SSMS displays conversion rates in the first result grid and all
    duplicate rows in the second result grid.

## Part 3: lead-conversion baseline

Open `lead_conversion_baseline.ipynb` in VS Code or Jupyter and run its cells from
top to bottom. Install the dependencies first if needed:

```powershell
python -m pip install -r requirements.txt
```

### Data decisions

- Normalize inconsistent city names and casing (`ISB`, `Rwp`, `khi`, and uppercase
  variants).
- Deduplicate on `crm_record_hash` before splitting, keeping the earliest record.
- Drop `lead_id` and `crm_record_hash` because identifiers do not generalize.
- Drop `token_amount_received_pkr` because it happens at/after conversion and almost
  directly reveals the outcome.
- Drop `first_response_minutes`, `calls_made`, `total_call_seconds`,
  `whatsapp_replies`, and `site_visits`. They are post-contact activity and would
  not exist when deciding which fresh lead to call first.
- Keep only intake-time lead attributes, and derive month, weekday, and hour from
  `created_at`.
- Impute missing values inside the training pipeline and use a chronological 80/20
  split instead of allowing future leads into training.

### Metric and result

Only 634 of 9,160 raw rows converted (6.92%), so accuracy would reward an useless
always-negative model. I report **Average Precision**, which evaluates how well the
model ranks rare conversions. Logistic regression achieved **0.209 AP** on the
newest 1,800 deduplicated leads, versus their **0.079 positive-rate/no-skill
baseline**. The model produces `predict_proba` scores suitable for prioritizing a
call list; they should not be presented as guaranteed conversion probabilities.

## Part 4: web interface

The Flask page includes both document Q&A with sources and the bonus lead-scoring
form. Install dependencies and configure Gemini in the same PowerShell window:

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace `your_gemini_api_key_here` in `.env` with a valid key, save it, then use the
one-command launcher:

```powershell
.\start.ps1
```

Open <http://127.0.0.1:5000> in a browser. The document assistant requires Gemini
for general questions; its deterministic safety cases still work without a key.
The lead model trains lazily on the first scoring request, so that first score can
take several seconds. Stop the server with `Ctrl+C`.

The real `.env` is intentionally excluded by `.gitignore`. API keys must not be
committed to a public submission; the reviewer should use their own key or receive a
fresh temporary key through a private channel. The included `.env.example` documents
the required settings without exposing credentials.
