# PART 5: FLOWS, CONFIGURATION & DEPLOYMENT

## 🔄 COMPLETE END-TO-END FLOWS

### Flow 1: User Onboarding

```
Step 1: User visits http://localhost:3000
        → Redirects to /login

Step 2: Click "Sign in with Google"
        → Frontend: authService.initiateGoogleLogin()
        → Redirect to: http://localhost:8000/auth/google
        → Backend redirects to Google OAuth consent screen

Step 3: User grants permissions (email, profile)
        → Google redirects to: http://localhost:8000/auth/google/callback?code={code}
        → Backend:
           a. Exchange code for tokens
           b. Verify ID token
           c. Create/update User in DB
           d. Generate JWT token
        → Redirect to: http://localhost:3000/auth/callback?token={jwt}

Step 4: Frontend AuthCallback page
        → Extract JWT from URL
        → Call GET /auth/me?token={jwt}
        → Store JWT and user in localStorage
        → Redirect to /dashboard

Step 5: User lands on Dashboard
        → Sees: Gmail status (not connected), Salesforce status (not connected)
```

---

### Flow 2: Connect Gmail

```
Step 1: Dashboard → "Connect Gmail" button
        → Frontend: gmailService.connectGmail(user.id)
        → Redirect to: http://localhost:8000/auth/gmail?user_id={id}

Step 2: Backend redirects to Google OAuth
        → Scope: gmail.readonly
        → State: user_id (passed back in callback)

Step 3: User grants Gmail permissions
        → Google redirects to: /auth/gmail/callback?code={code}&state={user_id}
        → Backend:
           a. Exchange code for tokens
           b. Store in oauth_connections (provider='gmail')
        → Redirect to: /dashboard?gmail_connected=true

Step 4: Dashboard shows "Gmail Connected ✅"
        → Can now fetch emails
```

---

### Flow 3: Connect Salesforce

```
Step 1: Dashboard → "Connect Salesforce" button
        → Frontend: window.location.href = /auth/salesforce?user_id={id}

Step 2: Backend redirects to Salesforce OAuth
        → URL: https://login.salesforce.com/services/oauth2/authorize
        → Scopes: api, refresh_token

Step 3: User logs into Salesforce + grants permissions
        → Salesforce redirects to: /auth/salesforce/callback?code={code}&state={user_id}
        → Backend:
           a. Exchange code for tokens
           b. Store tokens + instance_url in oauth_connections (provider='salesforce')
        → Redirect to: /dashboard?salesforce_connected=true

Step 4: Dashboard shows "Salesforce Connected ✅"
```

---

### Flow 4: Fetch & Process Emails (THE CORE FLOW)

```
Step 1: Dashboard → "Fetch Emails" button
        → Frontend: gmailService.fetchEmails(10)
        → POST /emails/fetch?max_results=10

Step 2: Backend (emails.py → fetch_emails):
        For each email:
        
        a. Fetch from Gmail API
           - gmail_service.fetch_sent_emails(user_id, db, 10)
           - Returns: list of message IDs
        
        b. Check for duplicates
           - Query email_logs by gmail_message_id
           - If exists: Skip
        
        c. Fetch email details
           - gmail_service.fetch_email_details(user_id, message_id, db)
           - Parse: subject, from, to, body, date
        
        d. Run AI extraction
           - ai_service.extract_crm_data(from, to, subject, body, date)
           - Call Azure OpenAI API
           - Parse JSON response
           - Calculate confidence score
        
        e. Classify email
           - If is_prospect_email = true → Status: "pending_review"
           - If is_prospect_email = false → Status: "rejected" (auto-reject)
        
        f. Store in database
           - Create EmailLog entry
           - Store ai_extracted_data (JSONB)
           - Store ai_confidence, is_prospect_email, status
        
        g. Commit to DB

Step 3: Backend returns summary:
        {
          "fetched": 5,
          "skipped": 2,
          "total": 7,
          "ai_extraction": { "success": 4, "failed": 1 }
        }

Step 4: Frontend updates Dashboard
        → Email stats refresh
        → User sees pending emails count increase
```

---

### Flow 5: Review & Approve Email

```
Step 1: Dashboard → Click "Pending (8)" card
        → Navigate to: /emails/pending

Step 2: EmailList page loads
        → GET /emails/list?status_filter=pending_review&limit=20&offset=0
        → Displays: 20 emails with preview

Step 3: User clicks an email
        → URL updates: /emails/pending?email={id}
        → EmailDetail sidebar opens
        → GET /emails/{id}
        → Shows:
           - Full email body
           - AI extracted data (expandable sections)
           - Salesforce preview (what will be created)

Step 4A: User edits AI data (optional)
        → Click "Edit" button
        → Modify contact name, company, opportunity details
        → Click "Save"
        → PUT /emails/{id}
        → Sets user_edited = true

Step 4B: User clicks "Approve"
        → POST /emails/{id}/approve
        
        Backend (emails.py → approve_email):
        
        a. Validate AI data exists
        
        b. Call Salesforce sync
           - salesforce_service.sync_email_to_salesforce()
           
           i. Find or Create Account
              - Search by domain → name
              - If not found: Create
              - Returns: account_id, account_created
           
           ii. Find or Create Contact
              - Search by email
              - If found: Update AccountId
              - If not found: Create
              - Returns: contact_id, contact_created
           
           iii. Find or Create Opportunity (conditional)
              - Check: opportunity.should_create = true?
              - If true: Search for open opp on Account
              - If not found: Create
              - Returns: opportunity_id, opportunity_created (or None)
           
           iv. Create Task
              - Subject: "Email: {email_subject}"
              - Status: Completed
              - Link to Contact (WhoId)
              - Link to Opportunity or Account (WhatId)
              - Returns: task_id
           
           v. Link Contact to Opportunity
              - If opportunity created: Create OpportunityContactRole
        
        c. Update email_log
           - Store Salesforce IDs (account_id, contact_id, opp_id, task_id)
           - Set status: "approved"
           - Set salesforce_synced: true
           - Set salesforce_sync_at: now()
        
        d. Return response:
           {
             "message": "Email approved and synced to Salesforce successfully",
             "salesforce": {
               "account_id": "001abc123",
               "contact_id": "003def456",
               "opportunity_id": "006ghi789",
               "task_id": "00Tjkl012",
               "account_created": true,
               "contact_created": false,
               "opportunity_created": true
             }
           }

Step 5: Frontend updates
        → Email moves from "Pending" to "Approved" list
        → Success message displayed
        → Salesforce IDs shown in detail view
```

---

### Flow 6: Reject Email

```
Step 1: User views email in EmailDetail
Step 2: Click "Reject" button
        → POST /emails/{id}/reject
Step 3: Backend:
        → Set status: "rejected"
        → No Salesforce sync
Step 4: Frontend:
        → Email moves to "Rejected" list
        → Can be restored later
```

---

### Flow 7: Restore Rejected Email

```
Step 1: Navigate to /emails/rejected
Step 2: Click rejected email
Step 3: Click "Restore" button
        → POST /emails/{id}/restore
Step 4: Backend:
        → Set status: "pending_review"
Step 5: Frontend:
        → Email moves back to "Pending" list
```

---

### Flow 8: Retry Failed Email

```
Step 1: Navigate to /emails/failed
Step 2: Click failed email (AI extraction error)
Step 3: Click "Retry" button
        → POST /emails/{id}/retry
Step 4: Backend:
        → Increment retry_count
        → Re-run AI extraction
        → If success: Set status "pending_review"
        → If fail: Keep status "failed"
Step 5: Frontend:
        → If success: Email moves to "Pending" list
        → If fail: Stays in "Failed" list
```

---

### Flow 9: Bulk Actions

```
Step 1: EmailList page
Step 2: Select multiple emails (checkboxes)
Step 3: Click "Approve Selected" or "Reject Selected"
        → POST /emails/bulk-approve or /emails/bulk-reject
        → Request: { "email_ids": [1, 2, 3, 4, 5] }
Step 4: Backend:
        → Update status for all emails
        → Return: counts (approved, rejected, failed)
Step 5: Frontend:
        → Emails move to appropriate lists
        → Success message with counts
```

---

## ⚙️ CONFIGURATION FILES

### Backend `.env` File

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autocrm_dev

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=10080  # 7 days

# Google OAuth (for login)
GOOGLE_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abcd1234efgh5678
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Gmail OAuth (for email access)
GMAIL_REDIRECT_URI=http://localhost:8000/auth/gmail/callback

# Google Cloud Pub/Sub (not implemented yet)
GOOGLE_CLOUD_PROJECT_ID=autocrm-123456
PUBSUB_TOPIC_NAME=gmail-notifications
PUBSUB_SUBSCRIPTION_NAME=gmail-notifications-sub

# Salesforce OAuth
SALESFORCE_CLIENT_ID=3MVG9...long-consumer-key...xyz
SALESFORCE_CLIENT_SECRET=1234567890ABCDEF
SALESFORCE_REDIRECT_URI=http://localhost:8000/auth/salesforce/callback

# Azure OpenAI API
AZURE_OPENAI_API_KEY=your-azure-api-key-here
AZURE_OPENAI_ENVIRONMENT_URL=your-environment-url.azure.com
AZURE_OPENAI_PROJECT_NAME=your-project-name
AZURE_OPENAI_DEPLOYMENT=ai-coe-gpt4o:analyze
AZURE_OPENAI_API_VERSION=2023-05-15

# App Settings
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development
```

### Frontend API Config (`src/services/api.js`)

```javascript
const API_BASE_URL = 'http://localhost:8000'

// For production:
// const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://api.autocrm.com'
```

### Database Connection

**PostgreSQL Connection String:**
```
postgresql://user:password@host:port/database
```

**Local Development:**
```
postgresql://postgres:postgres@localhost:5432/autocrm_dev
```

---

## 🚀 HOW TO RUN LOCALLY

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Google Cloud account (Gmail API + OAuth)
- Salesforce Developer account
- Azure OpenAI account

### Setup Steps

#### 1. Clone Repository
```bash
cd c:\Users\c9c4hx\Downloads\NewProjectASK\autocrm
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
# (Copy from example above and fill in credentials)

# Create database
# Option 1: Using psql
psql -U postgres
CREATE DATABASE autocrm_dev;
\q

# Option 2: Using pgAdmin (GUI)

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload
# Runs on: http://localhost:8000
```

#### 3. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# Runs on: http://localhost:3000
```

#### 4. Access Application
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (Swagger UI)

---

## 🧪 TESTING WORKFLOW

### Manual Testing Steps

**1. Test Authentication:**
```
→ Visit http://localhost:3000
→ Click "Sign in with Google"
→ Grant permissions
→ Should redirect to Dashboard
→ Should see user name and email
```

**2. Test Gmail Connection:**
```
→ Dashboard → "Connect Gmail"
→ Grant permissions
→ Should see "Gmail Connected ✅"
```

**3. Test Salesforce Connection:**
```
→ Dashboard → "Connect Salesforce"
→ Login to Salesforce Developer account
→ Grant permissions
→ Should see "Salesforce Connected ✅"
```

**4. Test Email Fetch:**
```
→ Dashboard → "Fetch Emails"
→ Wait for processing (10-30 seconds)
→ Should see: "Fetched X emails, AI extraction: Y success"
→ Email stats should update
```

**5. Test Email Review:**
```
→ Click "Pending (X)" card
→ Should see list of emails
→ Click an email
→ Should open detail sidebar
→ Review AI extracted data
→ Click "Approve"
→ Should see "Synced to Salesforce ✅"
→ Email should move to "Approved" list
```

**6. Verify in Salesforce:**
```
→ Login to Salesforce
→ Search for created Account
→ Check Contact is linked
→ Check Opportunity exists (if created)
→ Check Task is logged
```

---

## 📊 LOGGING & ERROR HANDLING

### Backend Logging
**Logger:** Python `logging` module  
**Log Level:** INFO (development), WARNING (production)

**What Gets Logged:**
- Gmail API calls (success/failure)
- AI extraction (start/success/failure)
- Salesforce sync (start/success/failure)
- Token refreshes
- Errors with stack traces

**Example Logs:**
```
INFO:app.services.gmail_service:Gmail service built for user 1
INFO:app.services.ai_service:Extracting CRM data from email: Q4 Pricing...
INFO:app.services.ai_service:AI extraction completed successfully
INFO:app.services.salesforce_service:Starting Salesforce sync for email 1...
INFO:app.services.salesforce_service:Found existing Account: 001abc123
INFO:app.services.salesforce_service:Created new Contact: 003def456
INFO:app.services.salesforce_service:Salesforce sync completed successfully
```

### Error Storage
- **Database Field:** `email_log.error_message`
- **Retry Count:** `email_log.retry_count`
- **Last Retry:** `email_log.last_retry_at`

### Common Errors & Solutions

**1. "Gmail not connected"**
- **Cause:** No oauth_connection with provider='gmail'
- **Solution:** Connect Gmail on Dashboard

**2. "Salesforce authentication failed"**
- **Cause:** Token expired, refresh failed
- **Solution:** Reconnect Salesforce

**3. "AI extraction failed: Invalid JSON"**
- **Cause:** AI returned malformed JSON
- **Solution:** Retry email, check prompt

**4. "Email has not been processed by AI yet"**
- **Cause:** Trying to approve email with no AI data
- **Solution:** Retry fetch or manual extract

**5. "Salesforce sync failed: Required field missing"**
- **Cause:** AI didn't extract company_name or email
- **Solution:** Edit email data, add missing fields, retry

---

## 📦 DEPLOYMENT (Future)

### Production Checklist

**Environment Variables:**
- [ ] Change JWT_SECRET_KEY (strong random string)
- [ ] Use production database URL
- [ ] Update FRONTEND_URL and BACKEND_URL
- [ ] Set ENVIRONMENT=production
- [ ] Use production OAuth redirect URIs

**Database:**
- [ ] Use managed PostgreSQL (Supabase, Railway, Render)
- [ ] Enable SSL connections
- [ ] Set up backups

**Security:**
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Encrypt OAuth tokens in DB
- [ ] Set up CORS properly
- [ ] Add input validation

**Monitoring:**
- [ ] Set up error tracking (Sentry)
- [ ] Set up logging (Papertrail, Loggly)
- [ ] Set up uptime monitoring

**OAuth Redirect URIs:**
- [ ] Update Google OAuth: https://api.yourdomain.com/auth/google/callback
- [ ] Update Gmail OAuth: https://api.yourdomain.com/auth/gmail/callback
- [ ] Update Salesforce OAuth: https://api.yourdomain.com/auth/salesforce/callback

**Deployment Platforms:**
- **Backend:** Railway, Render, Fly.io
- **Frontend:** Vercel, Netlify
- **Database:** Supabase, Railway, Render

---

## 🎯 CURRENT LIMITATIONS & FUTURE WORK

### Not Implemented (Yet)
- ❌ Gmail Push Notifications (manual fetch only)
- ❌ Background tasks (Celery + Redis configured but not used)
- ❌ Token encryption in database
- ❌ Rate limiting
- ❌ Caching (Salesforce data)
- ❌ Multi-user support
- ❌ Team features
- ❌ Custom field mapping
- ❌ Advanced analytics
- ❌ Email thread context (only single email)
- ❌ Attachment handling

### Known Issues
- No duplicate detection for Opportunities (creates multiple)
- No undo functionality for approved emails
- No bulk Salesforce sync (one at a time)
- No pagination on email fetch (max 10)

---

## 📞 SUPPORT & MAINTENANCE

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### Reset Database
```bash
# Drop all tables
alembic downgrade base

# Recreate tables
alembic upgrade head
```

### Clear Email Logs
```sql
DELETE FROM email_logs WHERE user_id = {user_id};
```

### Check OAuth Connections
```sql
SELECT user_id, provider, is_active, token_expires_at 
FROM oauth_connections;
```

---

## 🎉 PROJECT STATUS

**✅ Completed Phases:**
- Phase 1: Authentication (Google OAuth, JWT)
- Phase 2: Gmail Integration (OAuth, fetch emails)
- Phase 2.5: Email Management (list, detail, approve/reject)
- Phase 3: AI Extraction (Azure OpenAI)
- Phase 4: Salesforce Integration (OAuth, sync)

**🔮 Future Phases:**
- Phase 5: Gmail Push Notifications
- Phase 6: UI Polish & UX improvements
- Phase 7: Deployment & Production readiness
- Phase 8: Advanced features (analytics, custom fields, team features)

---

**Last Updated:** November 22, 2025  
**Version:** 1.0 (MVP)

