# PART 2: CODEBASE COMPONENTS & FILE DESCRIPTIONS

## 🔧 BACKEND FILES

### Core Application Files

**`app/main.py`** - FastAPI application entry point
- Creates FastAPI app with title, version
- Configures CORS middleware (allows frontend)
- Registers all API routers (auth, gmail, emails, salesforce)
- Root endpoint: `GET /` returns API info
- Health check: `GET /health`

**`app/config.py`** - Configuration management
- `Settings` class using Pydantic BaseSettings
- Loads from `.env` file
- Contains: DATABASE_URL, JWT secrets, OAuth credentials, Azure OpenAI config
- `get_settings()` returns cached singleton

**`app/database.py`** - Database connection
- Creates SQLAlchemy engine
- `SessionLocal` factory for DB sessions
- `Base` for model inheritance
- `get_db()` dependency yields DB session

---

### Models (Database Tables)

**`app/models/user.py`** - User model
```python
class User:
    id, google_id, email, name, picture
    company_name, company_domain  # For filtering internal emails
    created_at, last_login
    Relationship: oauth_connections, email_logs
```

**`app/models/oauth_connection.py`** - OAuth tokens
```python
class OAuthConnection:
    id, user_id, provider  # 'gmail' or 'salesforce'
    access_token, refresh_token, token_expires_at
    instance_url  # Salesforce instance
    connected_at, last_refresh, is_active
```

**`app/models/email_log.py`** - Email storage
```python
class EmailLog:
    # Gmail data
    gmail_message_id, gmail_thread_id
    from_email, to_email, cc_emails, subject, body_text, sent_date
    
    # AI extraction
    ai_extracted_data (JSONB), ai_confidence, is_prospect_email
    
    # Status & user interaction
    status, user_edited, user_edited_at
    
    # Salesforce sync
    salesforce_synced, salesforce_sync_at
    salesforce_contact_id, salesforce_account_id
    salesforce_opportunity_id, salesforce_task_id
    
    # Error handling
    error_message, retry_count, last_retry_at
```

---

### API Endpoints

**`app/api/auth.py`** - Authentication
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - Handle OAuth callback, create/update user, return JWT
- `GET /auth/me?token={jwt}` - Get current user info
- `POST /auth/logout` - Logout (client-side token removal)

**`app/api/gmail.py`** - Gmail connection
- `GET /auth/gmail?user_id={id}` - Initiate Gmail OAuth
- `GET /auth/gmail/callback` - Handle callback, store tokens
- `GET /auth/gmail/status` - Check Gmail connection status
- `POST /auth/gmail/disconnect` - Disconnect Gmail

**`app/api/salesforce.py`** - Salesforce connection
- `GET /auth/salesforce?user_id={id}` - Initiate Salesforce OAuth
- `GET /auth/salesforce/callback` - Handle callback, store tokens + instance_url
- `GET /auth/salesforce/status` - Check Salesforce connection status
- `POST /auth/salesforce/disconnect` - Disconnect Salesforce
- `POST /auth/salesforce/refresh` - Manually refresh token

**`app/api/emails.py`** - Email management (MAIN BUSINESS LOGIC)
- `POST /emails/fetch?max_results=10` - Fetch emails from Gmail + AI extraction
- `GET /emails/list?status_filter=&limit=50&offset=0` - List emails with pagination
- `GET /emails/{id}` - Get email details
- `GET /emails/stats/summary` - Get email counts by status
- `PUT /emails/{id}` - Update email (edit AI data)
- `POST /emails/{id}/approve` - Approve + Salesforce sync
- `POST /emails/{id}/reject` - Reject email
- `POST /emails/{id}/restore` - Restore rejected → pending
- `POST /emails/{id}/retry` - Retry failed email
- `POST /emails/{id}/extract` - Manually trigger AI extraction
- `POST /emails/bulk-approve` - Bulk approve emails
- `POST /emails/bulk-reject` - Bulk reject emails

---

### Services (Business Logic)

**`app/services/gmail_service.py`** - Gmail API integration
Key Functions:
- `get_gmail_service(user_id, db)` - Get authenticated Gmail client, auto-refresh token
- `fetch_sent_emails(user_id, db, max_results)` - Fetch sent emails from Gmail
- `fetch_email_details(user_id, message_id, db)` - Fetch full email content
- `parse_email_message(message)` - Parse Gmail API response into structured data
- `extract_email_address(string)` - Extract email from "Name <email>" format
- `extract_email_body(payload)` - Extract body from multipart messages
- `html_to_text(html)` - Convert HTML to plain text using BeautifulSoup

**`app/services/ai_service.py`** - Azure OpenAI integration
Key Functions:
- `get_azure_openai_client()` - Create Azure OpenAI client
- `build_extraction_prompt()` - Build prompt with email data
- `extract_crm_data(from, to, subject, body, date)` - Main extraction function
- `parse_ai_response(text)` - Parse JSON from AI, handle errors
- `calculate_field_completeness(data)` - Calculate completeness score (0.0-1.0)

AI Extraction Output Format:
```json
{
  "is_prospect_email": boolean,
  "contact": { "name", "email", "title", "phone" },
  "account": { "company_name", "domain", "industry", "size" },
  "opportunity": { "should_create", "stage", "amount", "close_date", "product", "competitors" },
  "activity": { "summary", "next_steps", "sentiment" },
  "follow_up": { "required", "date", "task_description" },
  "confidence": { "overall", "contact", "opportunity" }
}
```

**`app/services/salesforce_service.py`** - Salesforce integration
Key Functions:
- `get_salesforce_client(user_id, db)` - Get SF client, auto-refresh token
- `refresh_salesforce_token(user_id, db)` - Refresh expired token
- `find_or_create_account(sf, company, domain, industry, size)` - Search by domain → name → create
- `find_or_create_contact(sf, account_id, email, name, title, phone)` - Search by email → create
- `find_or_create_opportunity(sf, account_id, contact_id, opp_data, subject)` - Conditional creation
- `create_task(sf, contact_id, account_id, opp_id, subject, summary, next_steps, date)` - Log email activity
- `sync_email_to_salesforce(user_id, db, email_data, ai_data)` - Main sync orchestrator

Salesforce Objects Created:
1. **Account** - Company (find by Website/Name)
2. **Contact** - Person (find by Email)
3. **Opportunity** - Deal (only if `should_create=true`, find existing open opp)
4. **Task** - Email log (always created)
5. **OpportunityContactRole** - Links Contact to Opportunity

---

### Utilities

**`app/utils/jwt_handler.py`** - JWT management
- `create_access_token(data)` - Create JWT with 7-day expiry
- `verify_token(token)` - Verify and decode JWT

**`app/utils/dependencies.py`** - FastAPI dependencies
- `get_current_user_id(authorization)` - Extract user ID from Bearer token
- `get_current_user(user_id, db)` - Get User object from DB

---

## 🎨 FRONTEND FILES

### Core Files

**`src/main.jsx`** - React entry point
- Renders `<App />` into `#root`

**`src/App.jsx`** - Router configuration
Routes:
- `/login` → Login
- `/auth/callback` → AuthCallback (handles JWT from backend)
- `/dashboard` → Dashboard (protected)
- `/emails/all` → EmailList (all emails)
- `/emails/pending` → EmailList (pending)
- `/emails/approved` → EmailList (approved)
- `/emails/rejected` → EmailList (rejected)
- `/emails/failed` → EmailList (failed)
- `/` → Redirect to `/login`

---

### Pages

**`src/pages/Login.jsx`**
- "Sign in with Google" button
- Calls `authService.initiateGoogleLogin()` → redirects to `/auth/google`

**`src/pages/AuthCallback.jsx`**
- Receives `?token={jwt}` from backend
- Fetches user info: `GET /auth/me?token={jwt}`
- Stores JWT and user in localStorage
- Redirects to `/dashboard`

**`src/pages/Dashboard.jsx`**
- Shows user info, Gmail status, Salesforce status
- Email stats cards (clickable → navigate to EmailList)
- "Connect Gmail" / "Connect Salesforce" buttons
- "Fetch Emails" button → `POST /emails/fetch`
- Shows AI processing progress

**`src/pages/EmailList.jsx`**
- Lists emails by category (all/pending/approved/rejected/failed)
- Pagination (20 per page)
- Sorting (by date/subject, asc/desc)
- Select multiple emails → bulk approve/reject
- Click email → opens EmailDetail sidebar
- Status-specific actions (approve, reject, restore, retry)

---

### Components

**`src/components/ProtectedRoute.jsx`**
- Checks if JWT token exists in localStorage
- If not, redirect to `/login`
- If yes, render children

**`src/components/StatusBadge.jsx`**
- Color-coded badge for email status
- pending_review: 🟡 yellow
- approved: 🟢 green
- rejected: 🔴 red
- failed: ⚠️ orange

**`src/components/EmailCard.jsx`**
- Email list item component
- Shows: subject, recipient, date, status badge, confidence
- Checkbox for selection
- Click → opens detail sidebar

**`src/components/EmailDetail.jsx`**
- Right sidebar showing email details
- Email metadata (from, to, date, subject, body)
- AI extracted data in expandable sections
- Salesforce preview (what will be created)
- Action buttons (Approve, Reject, Edit, Close)

---

### Services

**`src/services/api.js`** - API client
- Axios instance with base URL `http://localhost:8000`
- Interceptors:
  - Request: Add `Authorization: Bearer {token}` header
  - Response: If 401, clear localStorage and redirect to login
  
Service Methods:
- `authService` - initiateGoogleLogin, getCurrentUser, logout
- `gmailService` - connectGmail, getStatus, disconnect, fetchEmails, getStats
- `emailService` - getEmails, getEmailDetails, updateEmail, approveEmail, rejectEmail, restoreEmail, retryEmail, extractEmail, bulkApprove, bulkReject
- `salesforceService` - getStatus, disconnect

---

## 🗂️ DATABASE MIGRATIONS

**`alembic/versions/5ef474bb3e23_initial_tables_users_and_oauth_.py`**
- Creates `users` and `oauth_connections` tables
- Indexes on: google_id, email, user_id

**`alembic/versions/72cc62aa9f4b_add_email_logs_table.py`**
- Creates `email_logs` table with JSONB column
- Indexes on: gmail_message_id (unique), gmail_thread_id, user_id, status

---

## 📦 DEPENDENCIES

### Backend (`requirements.txt`)
```
fastapi - Web framework
uvicorn[standard] - ASGI server
python-dotenv - Load .env
pydantic, pydantic-settings - Config validation
sqlalchemy - ORM
psycopg2-binary - PostgreSQL driver
alembic - Migrations
python-jose[cryptography] - JWT
passlib[bcrypt] - Password hashing (not used yet)
python-multipart - File uploads
google-auth, google-auth-oauthlib - Google OAuth
google-auth-httplib2, google-api-python-client - Gmail API
simple-salesforce - Salesforce API
openai - Azure OpenAI
httpx - HTTP client
tenacity - Retry logic
beautifulsoup4, bs4 - HTML parsing
celery, redis - Background tasks (not implemented yet)
```

### Frontend (`package.json`)
```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^6.26.0",
  "axios": "^1.7.2",
  "vite": "^5.4.1",
  "@vitejs/plugin-react": "^4.3.1"
}
```

---

## 🔑 KEY FUNCTIONS DEEP-DIVE

### Email Fetch Flow (`POST /emails/fetch`)
```python
1. Fetch sent emails from Gmail API
2. For each email:
   a. Check if already in DB (skip duplicates)
   b. Fetch full email details
   c. Run AI extraction (Azure OpenAI)
   d. Classify: is_prospect_email?
   e. Set status: pending_review (if prospect) or rejected (if not)
   f. Store in email_logs table
3. Return: fetched count, skipped count, AI success/failed counts
```

### Approve Email Flow (`POST /emails/{id}/approve`)
```python
1. Fetch email from DB
2. Validate: AI extraction exists
3. Call Salesforce sync:
   a. Find/create Account (search by domain → name)
   b. Find/create Contact (search by email)
   c. Find/create Opportunity (if should_create=true, check for open opps)
   d. Create Task (email log)
   e. Link OpportunityContactRole
4. Update email with Salesforce IDs
5. Set status: "approved"
6. Return: Salesforce IDs + created flags
```

### AI Extraction Logic
```python
1. Build prompt with email data
2. Call Azure OpenAI Chat Completion API
   - Model: ai-coe-gpt4o:analyze
   - Max tokens: 4000
   - Temperature: 0.0 (deterministic)
3. Parse JSON response (handle markdown code blocks)
4. Validate required fields
5. Calculate confidence:
   - AI model confidence (0.0-1.0)
   - Field completeness score (0.0-1.0)
   - Final: 70% AI + 30% completeness
6. Return: extracted_data, confidence, is_prospect_email
```

### Token Refresh Logic
- **Gmail:** Auto-refresh when expired using `google.auth` library
- **Salesforce:** Manual refresh using refresh_token (2-hour expiry)
- Happens automatically in `get_gmail_service()` and `get_salesforce_client()`

