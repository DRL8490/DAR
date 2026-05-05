# NMDC Survey Task Manager: Technical White Paper

**Version:** 3.2.0 (Stable Field Operations Build)  
**Core Function:** A Flask-based workflow engine that replaces chaotic email/spreadsheet survey requests with a rigid, auditable pipeline. It tracks execution dates for field accuracy and automates KPI, DTR, WSR, and TPC reporting.

---

## 1. System Architecture & Tech Stack

*   **Backend Framework:** Python 3.11 with Flask.
*   **Database:** PostgreSQL (via Flask-SQLAlchemy) managed on Render.com.
*   **Authentication:** Flask-Login with werkzeug PBKDF2 password hashing.
*   **Frontend UI:** HTML5, CSS3, native JavaScript, Bootstrap 5 (CDN), FontAwesome.
*   **Document Generation:** `docxtpl` (Word templates) and `pandas` / `openpyxl` (Excel KPI generation).
*   **Background Tasks:** `APScheduler` (Cron jobs running in the Flask app context).
*   **Email Engine:** `Flask-Mail` (SMTP via Gmail App Passwords).

---

## 2. Database Schema (The Data Layer)

The application relies on four core database models.

### A. `User` (Identity & Access)
*   **Fields:** `id`, `email`, `name`, `password_hash`, `is_approved`, `is_active`, `is_admin`.
*   **VIP Logic:** An internal `@property def is_vip(self)` grants admin rights if the user's email is in the hard-coded `ADMIN_EMAILS` list OR if their database `is_admin` flag is `True`.

### B. `SurveyTask` (The Core Record)
*   **Tracking Fields:** `id`, `surveyor_name`, `assigned_to` (comma-separated), `requestor`.
*   **Categorization:** `task_category`, `action_required`, `instrument`, `area`, `location`, `sub_location`, `work_scope`.
*   **Status & Metadata:** `status` (`Open`, `Closed`, `Canceled`, `Archived`), `is_urgent` (boolean), `remarks`, `reference_links`, `deliverable_link`.
*   **Time Logic (CRITICAL):**
    *   `start_time`: System audit timestamp (immutable). Dictates official Sequence IDs (e.g., `TW_05001`).
    *   `execution_date`: Business audit date (mutable via Edit page). Overrides the visual display date on Excel KPIs and Word DTR/WSRs to accurately log late-filed field reports.
    *   `end_time`: System timestamp when the task is marked Closed or Canceled.

### C. `AppConfig` (The Master JSON Schema)
*   A single-row table storing a global JSON string containing three core dictionaries:
    1.  `file_tree`: A 4-level deep cascade of Area ➔ Location ➔ Sub-Location ➔ Scope.
    2.  `requestors`: Departments and their associated personnel.
    3.  `activities`: Activity Types ➔ Actions ➔ Instruments.

### D. `PresetTask` (User Convenience)
*   Saves a user's exact dropdown selections for rapid form filling on future tasks. Tied directly to `user_id`.

---

## 3. Core Workflow Engines

### A. The Task Lifecycle
The application uses a strict, two-step operational lifecycle to maintain pipeline velocity:
1.  **Creation:** Users generate tasks, which default to the `Open` status and enter the active dashboard queue.
2.  **Resolution:** Assigned surveyors (or admins) click "Complete Task" (requiring closing remarks and optional deliverable links) or "Cancel Task" (requiring a cancellation reason). This timestamps the `end_time`.

### B. Client-Side JSON Caching (The Dropdown Engine)
To prevent server lag and constant database pinging, the massive `AppConfig` JSON dictionaries are injected directly into the HTML `<script>` tags on the `/new_task` and `/edit_task` pages. JavaScript functions (`updateLocations()`, `updateActions()`) filter the subsequent dropdowns instantly on the client side based on user selection.

### C. Smart Search (Quick Find)
A custom JavaScript engine maps the complex `activities` JSON into a flat, searchable list of strings (e.g., `Land Survey ➔ Pre-Survey ➔ GNSS Rover`). The user types a keyword, selects the matched string, and the script automatically forces the cascading dropdowns (Activity Type, Action, Instrument) to populate correctly.

---

## 4. Reporting & Analytics

### A. The KPI Engine (`/export_excel`)
*   Filters out "administrative" tasks (meetings, general reports) from field performance metrics.
*   Sorts chronologically by the immutable `start_time` to generate sequential reference strings (e.g., `TW_05001`).
*   **The Visual Override:** If an `execution_date` was logged by the surveyor, the engine prints *that* date into the final Excel columns instead of the system timestamp. This ensures accurate field-work visualization without corrupting the background sequence math.

### B. Word Document Generators (`docxtpl`)
*   **DTR (Daily):** Groups tasks by operational vessel/location (e.g., EGST Hydro Survey, Arzana, Onshore) for a specific target date. Query logic explicitly checks for matching `execution_date` overrides first, falling back to `start_time`.
*   **WSR (Weekly):** Loops through 7 consecutive days, running the DTR logic for each day, and injects the blocks into a comprehensive weekly summary template.
*   **TPC (Custom Weekly):** A customized report targeting a Thursday-to-Wednesday cycle. Extracts unique work scopes into deduplicated "Done" and "Planned" bulleted lists.

---

## 5. Background Automation (APScheduler)

Two jobs run silently within the Flask application context:
1.  **The Auto-Archiver (Every 12 hours):** Scans the database for `Closed` tasks where the `end_time` is older than 31 days. Moves their status to `Archived` to keep the main dashboard UI lightning fast.
2.  **The Nightly KPI Backup (Daily at 15:59 UTC / 23:59 Taiwan Local):** Runs the exact KPI Engine logic, formats the `pandas` DataFrame into an `openpyxl` Excel file in memory, and emails it directly to the `ADMIN_EMAILS` list using `Flask-Mail`.

---

## 6. Admin Control & Security

### A. The User Control Panel (`/manage_users`)
*   A dedicated, admin-only portal for managing the team roster.
*   Allows VIPs to approve pending registrations, deactivate rogue/former users, and permanently hard-delete accounts.
*   Allows VIPs to dynamically promote Standard users to Admin status via the `is_admin` database toggle, replacing hard-coded environment variables.

### B. Migration Engine (`/migrate`)
*   A powerful ETL (Extract, Transform, Load) route that accepts legacy `.xlsx` files. 
*   Parses rows dynamically by hunting for loose column headers like "From Date" and "Activity Type". 
*   Mass-injects historical spreadsheet data directly into the `SurveyTask` database as `Closed` tasks for permanent querying and KPI continuity.

---

## 7. Application Front-End Map & Access Control

We use three logic tiers to control access to these pages, managed by `flask-login`'s `@login_required` decorator and custom role checks.

### Tier 1: Public/Anonymous (No Login Required)
These pages handle authentication setup.

| Page Template | Route | Description |
| :--- | :--- | :--- |
| `login.html` | `/login` | Entry point. Handles email/password checking and directs users to their dashboard. |
| `register.html` | `/register` | Allows new NMDC surveyors to create an account (`is_approved = False`). |
| `forgot_password.html`| `/forgot-password` | Form to request a secure password reset link via email. |
| `reset_password.html` | `/reset-password/<token>`| Form to set a new password, validated by a secure, time-limited token. |

### Tier 2: Approved Surveyor (Login & `is_approved = True` Required)
These are standard workflow pages for field surveyors.

| Page Template | Route | Description | Access Logic |
| :--- | :--- | :--- | :--- |
| `dashboard.html` | `/` or `/dashboard` | The primary operational view. Displays the pipeline of `Open` tasks, sorted by urgency and date. | Standard Approved User. |
| `new_task.html` | `/new_task` | The complex form for opening a new request. Uses Smart Search and cascading JS dropdowns. | Standard Approved User. |
| `edit_task.html` | `/edit_task/<int:id>`| Form to modify existing tasks. Includes the "Backdate Survey Execution" override box. | Standard Approved User (if they are the creator or assignee) OR Admin. |

### Tier 3: VIP Admin (Login & `is_vip = True` Required)
These pages handle sensitive administration, advanced configuration, and report generation.

| Page Template | Route | Description | Access Logic |
| :--- | :--- | :--- | :--- |
| `admin_dashboard.html`| `/admin_dashboard` | Enhanced main dashboard for supervisors. Features Chart.js analytics of pipeline velocity and master data filters. | VIP Admin (`is_vip`) Only. |
| `manage_users.html` | `/manage_users` | The dynamic User Control Panel. (Approvals, deactivations, dynamic `is_admin` toggles). | VIP Admin (`is_vip`) Only. |
| `reports.html` | `/reports` | A clean interface with manual download buttons for KPI Excel, DTR, WSR, and TPC reports. | VIP Admin (`is_vip`) Only. |
| `hidden_admin.html` | `/system_config_hidden`| A restricted interface for editing the JSON master schema (file tree, requestor list, activity list). | VIP Admin (`is_vip`) Only. |
| `cleanup.html` | `/cleanup` | A data hygiene page for permanently deleting (`db.session.delete()`) old or incorrect tasks from the database. | VIP Admin (`is_vip`) Only. |
| `archive.html` | `/archive` | A page to view and restore (`Archived` ➔ `Closed`) tasks that were automatically moved by the 31-day scheduler. | VIP Admin (`is_vip`) Only. |
| `migration.html` | `/migrate` | Upload portal for bulk importing historical spreadsheet data into the database. | VIP Admin (`is_vip`) Only. |