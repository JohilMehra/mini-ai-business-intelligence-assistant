# Development Notes

## 1. Project Summary

The AI Business Intelligence Assistant is a local web application that
answers a defined set of sales-analysis questions in natural language.
The frontend uses React and Vite. The backend uses Python and FastAPI,
imports the supplied CSV with Pandas, and stores transaction data in
SQLite.

Supported questions: - Total net revenue - Highest-revenue product -
Monthly revenue trend - Highest-revenue region - Revenue comparison
between two specified months

Financial values are calculated by the application's database-backed
analytics logic. Gemini interprets a question into an allowed intent; it
is not responsible for calculating financial figures or generating
executable SQL.

## 2. AI Tools Used

### OpenAI Codex

OpenAI Codex assisted with generating and refining application code and
documentation from the project requirements. It was also used to inspect
the implementation, run checks, and investigate build and dependency
issues.

### Google Gemini API

The application includes optional Gemini-powered question interpretation
through Google's `google-genai` Python SDK. The backend reads its API
key and model configuration from `backend/.env`. The key must remain
private and must never be included in frontend code, documentation,
terminal logs, or the Git repository.

A deterministic fallback supports common question patterns when Gemini
is not configured or a Gemini request fails. A successful live Gemini
request should only be claimed after it has been verified separately.

## 3. Development Challenges and Resolutions

### CSV filename and data validation

The original supplied file was named `sales.csv.csv` in the project
root. It was preserved and copied to `backend/data/sales.csv` for
application use. The files had matching SHA-256 hashes when copied.

The dataset contains 51 transaction rows. The agreed policy excludes
returned transactions and records with missing required values or
invalid numeric values from revenue calculations. The verified result
was 49 eligible records and 2 excluded records. Excluded records are
retained for review with a reason, rather than being counted in revenue
totals.

### Repeat-safe database import

The application imports the CSV into a local SQLite database at
`backend/data/sales.db`. The import was checked for repeatability so
starting the application again would not duplicate the source records.

### Python environment setup

The local Windows environment initially encountered a Python
virtual-environment/pip setup issue. A virtual environment was created
without pip and pip was bootstrapped into it before installing the
project requirements. The Python dependencies were then checked, and the
backend tests passed.

### Frontend dependency advisories

The initial frontend dependency audit reported vulnerabilities in the
installed Vite/esbuild dependency tree. Vite was updated to a compatible
Vite 6 release while keeping the existing React plugin and application
architecture. A lockfile was generated. The subsequent audit reported
zero vulnerabilities, the production build succeeded, and the backend
tests passed again.

### Gemini configuration and safe fallback

The Gemini integration was configured to read the model and API key from
environment variables. The fallback path allows common supported
questions to be interpreted without requiring a successful Gemini
request. The application uses an allowlist of supported analytics
intents and rejects unsupported questions rather than treating arbitrary
user text as SQL.

## 4. Debugging and Verification

The following checks were reported during development:

-   CSV import: 51 rows imported; 49 eligible for revenue calculations
    and 2 excluded.
-   Revenue calculation: total net revenue of ₹1,439,200.
-   Top product: Monitor, with revenue of ₹473,000.
-   Top region: South, with revenue of ₹411,200.
-   Monthly revenue values were checked against the imported dataset.
-   Backend automated test suite: 8 tests passed.
-   Frontend production build: succeeded.
-   Frontend dependency audit after the Vite update: 0 vulnerabilities
    reported.
-   Manual dashboard testing covered all five supported business
    questions.
-   Unsupported and blank questions were manually tested and reported as
    handled safely.

**Verification limitation:** the project was configured for Gemini and
the dashboard displayed a "GEMINI INTERPRETATION" label during manual
use, but a successful live Gemini API request was not conclusively
verified in the development notes available here. Do not claim the live
integration was verified unless a real successful request is confirmed.

The destructive-request test should also be recorded as complete only if
it was actually run and the database record count was confirmed
unchanged.

## 5. Current Limitations

-   Question interpretation intentionally supports a small, predefined
    set of business intents.
-   Gemini interpretation requires a valid API key, an available model,
    internet access, and available API quota.
-   The deterministic fallback only handles supported common question
    patterns.
-   The chart is a lightweight CSS-based bar chart.
-   Currency display uses INR formatting.
-   Month comparisons require two `YYYY-MM` values.
-   The local SQLite database is generated application data and should
    not be committed unless explicitly required.

## 6. Improvements With One Additional Day

If one additional day were available, the following improvements would
be prioritized:

1.  Expand automated tests for varied natural-language phrasing,
    malformed comparison dates, empty datasets, and additional invalid
    records.
2.  Confirm the live Gemini request path, including invalid-key, quota,
    timeout, and fallback behavior.
3.  Improve user-facing error messages while keeping diagnostic logs
    free of secrets.
4.  Improve chart accessibility and responsiveness.
5.  Add configurable date ranges and more flexible comparison questions.
6.  Review the repository and submission package for reproducible setup,
    secret protection, and complete documentation.

## 7. Reproducibility and Security Notes

-   Backend dependencies are listed in `backend/requirements.txt`.
-   Frontend dependencies and resolved versions are recorded in
    `frontend/package.json` and `frontend/package-lock.json`.
-   Run backend tests from `backend/` with `python -m pytest -q`.
-   Build the frontend from `frontend/` with `npm run build`.
-   Keep `backend/.env`, virtual environments, `node_modules`, generated
    build output, temporary test files, and the local SQLite database
    out of version control.
-   Include the supplied application CSV at `backend/data/sales.csv`.
-   Never commit or share the Gemini API key.
