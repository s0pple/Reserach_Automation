# Feature Plan: Global Research Database

## Goal
Implement a structured database to store the results of all completed Venture Research pipelines (specifically the structured data from `VentureState` and the final Markdown memos). This prevents data loss across multiple runs and allows future agents to query historical research.

## Architecture & Tech Stack
- **Storage Type:** SQLite (Local file-based, minimal setup, perfect for MVP and Docker portability). We can upgrade to Postgres later if scaling requires it.
- **ORM:** SQLAlchemy (Standard, robust Python ORM).
- **Target Location:** `data/research.db`.

## Data Schema
We need to persist the core elements of the `VentureState`.

**Table: `research_runs`**
- `id`: Integer, Primary Key
- `domain`: String (e.g., "AI for Legal Compliance")
- `date_run`: DateTime (Timestamp of the run)
- `total_claims_extracted`: Integer
- `top_opportunity_score`: Float
- `status`: String (e.g., "Completed", "Failed")

**Table: `opportunities` (Links to `research_runs.id`)**
- `id`: Integer, Primary Key
- `run_id`: Integer, Foreign Key -> `research_runs.id`
- `title`: String (e.g., "Automated KYC/AML Compliance Platform")
- `score`: Float (The Venture Score)
- `rationale`: Text (The "DIE WAFFE" section)
- `memo_markdown`: Text (The full generated markdown memo)

## Execution Phases for the Worker Agent

### Phase 1: Database Setup & ORM
1. Create a new module: `src/modules/db/database.py`.
2. Implement the SQLAlchemy engine pointing to `sqlite:///data/research.db`.
3. Create the SQLAlchemy Models for `ResearchRun` and `Opportunity` matching the schema above.
4. Add a function `init_db()` that creates the tables if they don't exist.

### Phase 2: Integration into the Pipeline
1. Modify `run_venture_analyst.py`.
2. Import `init_db` and call it at the very start of the script.
3. At the end of the `[3/4] DONE: Venture Memos have been generated` step, just before the Deep Research phase:
   - Instantiate a database session.
   - Create a `ResearchRun` record based on the `VentureState`.
   - Iterate through `state.nodes` (the opportunities) and create an `Opportunity` record for each, linking it to the run.
   - Extract the generated markdown memo from `state.metadata.get("venture_memos")` and store it in the respective opportunity record.
   - Commit the session.

### Phase 3: Validation (Shift-Left Quality Gate)
1. Write a simple Python script `scripts/view_db.py` that queries and prints the last 5 `research_runs` and their associated `opportunities` to the console.
2. The agent must run a test pipeline (using the synthetic data injection) and then run `scripts/view_db.py` to prove the data was saved correctly.

## Constraints & Rules (Manager Directives)
- **Do NOT modify existing agent logic** (e.g., EvidenceExtractor, Historian). The database should act purely as a "sink" at the end of the pipeline.
- **Simplicity:** Keep the SQLAlchemy models basic. Do not over-engineer relationships we don't need yet.
- **Isolation:** If the database insert fails, it should log a warning but should NOT crash the rest of the script (especially Phase 4 Deep Research). Wrap the DB insert in a try-except block.