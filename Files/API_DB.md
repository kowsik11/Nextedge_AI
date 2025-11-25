# PART 3: COMPLETE API DOCUMENTATION & DATABASE

## 📡 API ENDPOINTS

Base URL: `http://localhost:8000`

---

### 🔐 Authentication Endpoints

#### `GET /auth/google`
**Purpose:** Initiate Google OAuth login flow  
**Method:** GET  
**Auth:** None  
**Request:** None  
**Response:** Redirect to Google OAuth consent screen  
**Frontend Trigger:** Login page "Sign in with Google" button  
**File:** `app/api/auth.py`

---

#### `GET /auth/google/callback?code={code}`
**Purpose:** Handle Google OAuth callback  
**Method:** GET  
**Auth:** None  
**Query Params:**
- `code` - Authorization code from Google

**Process:**
1. Exchange code for tokens
2. Verify ID token
3. Create/update user in DB
4. Generate JWT token

**Response:** Redirect to frontend: `http://localhost:3000/auth/callback?token={jwt}`  
**Frontend Trigger:** Automatic (Google redirects here)  
**File:** `app/api/auth.py`

---

#### `GET /auth/me?token={jwt}`
**Purpose:** Get current user info  
**Method:** GET  
**Auth:** Query param `token`  
**Request:** Query param `token={jwt}`  
**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "picture": "https://...",
  "company_name": "Acme Corp",
  "company_domain": "acme.com"
}
```
**Frontend Trigger:** AuthCallback page (after login)  
**File:** `app/api/auth.py`

---

#### `POST /auth/logout`
**Purpose:** Logout (client-side token removal)  
**Method:** POST  
**Auth:** Bearer token  
**Response:** `{ "message": "Logged out successfully" }`  
**Frontend Trigger:** Logout button  
**File:** `app/api/auth.py`

---

### 📧 Gmail Endpoints

#### `GET /auth/gmail?user_id={id}`
**Purpose:** Initiate Gmail OAuth  
**Method:** GET  
**Auth:** None  
**Query Params:** `user_id` - User ID to connect Gmail to  
**Response:** Redirect to Google OAuth consent (scope: gmail.readonly)  
**Frontend Trigger:** Dashboard "Connect Gmail" button  
**File:** `app/api/gmail.py`

---

#### `GET /auth/gmail/callback?code={code}&state={user_id}`
**Purpose:** Handle Gmail OAuth callback  
**Method:** GET  
**Auth:** None  
**Query Params:**
- `code` - Authorization code
- `state` - User ID

**Process:**
1. Exchange code for tokens
2. Store in `oauth_connections` table
3. Redirect to dashboard

**Response:** Redirect: `http://localhost:3000/dashboard?gmail_connected=true`  
**Frontend Trigger:** Automatic  
**File:** `app/api/gmail.py`

---

#### `GET /auth/gmail/status`
**Purpose:** Check Gmail connection status  
**Method:** GET  
**Auth:** Bearer token  
**Response:**
```json
{
  "connected": true,
  "is_expired": false,
  "connected_at": "2025-11-22T10:00:00Z",
  "last_refresh": "2025-11-22T12:00:00Z"
}
```
**Frontend Trigger:** Dashboard load  
**File:** `app/api/gmail.py`

---

#### `POST /auth/gmail/disconnect`
**Purpose:** Disconnect Gmail  
**Method:** POST  
**Auth:** Bearer token  
**Response:** `{ "message": "Gmail disconnected successfully" }`  
**Frontend Trigger:** Dashboard "Disconnect" button  
**File:** `app/api/gmail.py`

---

### 🏢 Salesforce Endpoints

#### `GET /auth/salesforce?user_id={id}`
**Purpose:** Initiate Salesforce OAuth  
**Method:** GET  
**Auth:** None  
**Query Params:** `user_id`  
**Response:** Redirect to Salesforce OAuth (scope: api, refresh_token)  
**Frontend Trigger:** Dashboard "Connect Salesforce" button  
**File:** `app/api/salesforce.py`

---

#### `GET /auth/salesforce/callback?code={code}&state={user_id}`
**Purpose:** Handle Salesforce OAuth callback  
**Method:** GET  
**Auth:** None  
**Query Params:** `code`, `state`  
**Process:**
1. Exchange code for tokens
2. Store tokens + instance_url in DB
3. Redirect to dashboard

**Response:** Redirect: `http://localhost:3000/dashboard?salesforce_connected=true`  
**Error Redirect:** `?salesforce_error={message}`  
**Frontend Trigger:** Automatic  
**File:** `app/api/salesforce.py`

---

#### `GET /auth/salesforce/status`
**Purpose:** Check Salesforce connection  
**Method:** GET  
**Auth:** Bearer token  
**Response:**
```json
{
  "connected": true,
  "instance_url": "https://na123.my.salesforce.com",
  "is_expired": false,
  "connected_at": "2025-11-22T10:00:00Z",
  "last_refresh": "2025-11-22T11:00:00Z"
}
```
**Frontend Trigger:** Dashboard load  
**File:** `app/api/salesforce.py`

---

#### `POST /auth/salesforce/disconnect`
**Purpose:** Disconnect Salesforce  
**Method:** POST  
**Auth:** Bearer token  
**Response:** `{ "message": "Salesforce disconnected successfully" }`  
**Frontend Trigger:** Dashboard "Disconnect" button  
**File:** `app/api/salesforce.py`

---

#### `POST /auth/salesforce/refresh`
**Purpose:** Manually refresh token  
**Method:** POST  
**Auth:** Bearer token  
**Response:**
```json
{
  "message": "Token refreshed successfully",
  "expires_at": "2025-11-22T14:00:00Z"
}
```
**Frontend Trigger:** Manual action (rare)  
**File:** `app/api/salesforce.py`

---

### ✉️ Email Management Endpoints

#### `POST /emails/fetch?max_results={n}`
**Purpose:** Fetch sent emails from Gmail + run AI extraction  
**Method:** POST  
**Auth:** Bearer token  
**Query Params:** `max_results` (default: 10)  
**Process:**
1. Fetch sent emails from Gmail
2. Skip duplicates
3. Run AI extraction on each email
4. Store in email_logs table

**Response:**
```json
{
  "message": "Emails fetched and processed successfully",
  "fetched": 5,
  "skipped": 2,
  "total": 7,
  "ai_extraction": {
    "success": 4,
    "failed": 1
  }
}
```
**Frontend Trigger:** Dashboard "Fetch Emails" button  
**File:** `app/api/emails.py` → `fetch_emails()`

---

#### `GET /emails/list?status_filter={status}&limit={n}&offset={n}&sort_by={field}&sort_order={order}`
**Purpose:** List emails with filtering, sorting, pagination  
**Method:** GET  
**Auth:** Bearer token  
**Query Params:**
- `status_filter` - all, pending_review, approved, rejected, failed (optional)
- `limit` - default: 50
- `offset` - default: 0
- `sort_by` - sent_date, created_at, subject (default: sent_date)
- `sort_order` - asc, desc (default: desc)

**Response:**
```json
{
  "total": 42,
  "count": 20,
  "offset": 0,
  "limit": 20,
  "emails": [
    {
      "id": 1,
      "subject": "Q4 Pricing Proposal - Acme Corp",
      "to_email": "john@acme.com",
      "from_email": "you@company.com",
      "sent_date": "2025-11-22T10:00:00Z",
      "status": "pending_review",
      "ai_confidence": 0.87,
      "body_preview": "Hi John, Following up on our call...",
      "created_at": "2025-11-22T10:05:00Z"
    }
  ]
}
```
**Frontend Trigger:** EmailList page load  
**File:** `app/api/emails.py` → `list_emails()`

---

#### `GET /emails/{id}`
**Purpose:** Get full email details  
**Method:** GET  
**Auth:** Bearer token  
**URL Params:** `id` - email_log ID  
**Response:**
```json
{
  "id": 1,
  "gmail_message_id": "18c1234567890abcd",
  "subject": "Q4 Pricing Proposal",
  "from_email": "you@company.com",
  "to_email": "john@acme.com",
  "cc_emails": null,
  "body_text": "Full email body...",
  "sent_date": "2025-11-22T10:00:00Z",
  "status": "pending_review",
  "ai_extracted_data": {
    "contact": { "name": "John Smith", "email": "john@acme.com", "title": "VP Sales" },
    "account": { "company_name": "Acme Corp", "domain": "acme.com" },
    "opportunity": { "should_create": true, "stage": "Proposal", "amount": 50000 },
    "activity": { "summary": "Sent pricing proposal for Q4 deal" }
  },
  "ai_confidence": 0.87,
  "salesforce_synced": false,
  "salesforce_contact_id": null,
  "created_at": "2025-11-22T10:05:00Z"
}
```
**Frontend Trigger:** Click email in list → EmailDetail sidebar  
**File:** `app/api/emails.py` → `get_email_details()`

---

#### `GET /emails/stats/summary`
**Purpose:** Get email counts by status  
**Method:** GET  
**Auth:** Bearer token  
**Response:**
```json
{
  "total": 42,
  "pending_review": 8,
  "approved": 25,
  "rejected": 7,
  "failed": 2
}
```
**Frontend Trigger:** Dashboard load  
**File:** `app/api/emails.py` → `get_email_stats()`

---

#### `PUT /emails/{id}`
**Purpose:** Update email (edit AI extracted data)  
**Method:** PUT  
**Auth:** Bearer token  
**URL Params:** `id`  
**Request Body:**
```json
{
  "ai_extracted_data": {
    "contact": { "name": "John Doe", "email": "john@acme.com", "title": "CEO" },
    "account": { "company_name": "Acme Corporation" }
  },
  "user_edited": true
}
```
**Response:**
```json
{
  "message": "Email updated successfully",
  "email_id": 1,
  "status": "pending_review"
}
```
**Frontend Trigger:** EmailDetail "Save" button after editing  
**File:** `app/api/emails.py` → `update_email()`

---

#### `POST /emails/{id}/approve`
**Purpose:** Approve email → sync to Salesforce  
**Method:** POST  
**Auth:** Bearer token  
**URL Params:** `id`  
**Process:**
1. Validate AI data exists
2. Sync to Salesforce (Account, Contact, Opportunity, Task)
3. Store Salesforce IDs
4. Set status: "approved"

**Response (Success):**
```json
{
  "message": "Email approved and synced to Salesforce successfully",
  "email_id": 1,
  "status": "approved",
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
```
**Response (Error 500):**
```json
{
  "detail": "Email approved but Salesforce sync failed: {error}"
}
```
**Frontend Trigger:** EmailDetail "Approve" button  
**File:** `app/api/emails.py` → `approve_email()`

---

#### `POST /emails/{id}/reject`
**Purpose:** Reject email (will not sync to Salesforce)  
**Method:** POST  
**Auth:** Bearer token  
**URL Params:** `id`  
**Response:**
```json
{
  "message": "Email rejected successfully",
  "email_id": 1,
  "status": "rejected"
}
```
**Frontend Trigger:** EmailDetail "Reject" button  
**File:** `app/api/emails.py` → `reject_email()`

---

#### `POST /emails/{id}/restore`
**Purpose:** Restore rejected email to pending_review  
**Method:** POST  
**Auth:** Bearer token  
**URL Params:** `id`  
**Response:**
```json
{
  "message": "Email restored to pending review",
  "email_id": 1,
  "status": "pending_review"
}
```
**Frontend Trigger:** Rejected emails "Restore" button  
**File:** `app/api/emails.py` → `restore_email()`

---

#### `POST /emails/{id}/retry`
**Purpose:** Retry failed email (re-run AI extraction)  
**Method:** POST  
**Auth:** Bearer token  
**URL Params:** `id`  
**Response:**
```json
{
  "message": "Email retry completed",
  "email_id": 1,
  "status": "pending_review",
  "retry_count": 2
}
```
**Frontend Trigger:** Failed emails "Retry" button  
**File:** `app/api/emails.py` → `retry_email()`

---

#### `POST /emails/{id}/extract`
**Purpose:** Manually trigger AI extraction  
**Method:** POST  
**Auth:** Bearer token  
**URL Params:** `id`  
**Response:**
```json
{
  "message": "AI extraction completed successfully",
  "email_id": 1,
  "ai_confidence": 0.89,
  "is_prospect_email": true,
  "extracted_data": { ... }
}
```
**Frontend Trigger:** Manual action (admin/testing)  
**File:** `app/api/emails.py` → `manual_extract_email()`

---

#### `POST /emails/bulk-approve`
**Purpose:** Approve multiple emails at once  
**Method:** POST  
**Auth:** Bearer token  
**Request Body:**
```json
{
  "email_ids": [1, 2, 3, 4, 5]
}
```
**Response:**
```json
{
  "message": "Bulk approve completed",
  "total_requested": 5,
  "approved": 5,
  "failed": 0,
  "failed_ids": []
}
```
**Frontend Trigger:** EmailList bulk actions  
**File:** `app/api/emails.py` → `bulk_approve_emails()`

---

#### `POST /emails/bulk-reject`
**Purpose:** Reject multiple emails at once  
**Method:** POST  
**Auth:** Bearer token  
**Request Body:**
```json
{
  "email_ids": [1, 2, 3]
}
```
**Response:**
```json
{
  "message": "Bulk reject completed",
  "total_requested": 3,
  "rejected": 3,
  "failed": 0,
  "failed_ids": []
}
```
**Frontend Trigger:** EmailList bulk actions  
**File:** `app/api/emails.py` → `bulk_reject_emails()`

---

## 🗄️ DATABASE SCHEMA DETAILS

### Table: `users`
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture VARCHAR(500),
    company_name VARCHAR(255),
    company_domain VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_users_google_id ON users(google_id);
CREATE INDEX idx_users_email ON users(email);
```

### Table: `oauth_connections`
```sql
CREATE TABLE oauth_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- 'gmail' or 'salesforce'
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    scope TEXT,
    provider_user_id VARCHAR(255),
    instance_url VARCHAR(255),
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_refresh TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, provider)
);

-- Indexes
CREATE INDEX idx_oauth_user_id ON oauth_connections(user_id);
CREATE INDEX idx_oauth_provider ON oauth_connections(provider);
```

### Table: `email_logs`
```sql
CREATE TABLE email_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Gmail data
    gmail_message_id VARCHAR(255) UNIQUE NOT NULL,
    gmail_thread_id VARCHAR(255),
    from_email VARCHAR(255),
    to_email VARCHAR(255),
    cc_emails TEXT,
    subject TEXT,
    body_text TEXT,
    sent_date TIMESTAMP WITH TIME ZONE,
    
    -- AI extraction (PostgreSQL JSONB)
    ai_extracted_data JSONB,
    ai_confidence FLOAT,
    is_prospect_email BOOLEAN,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending_review',
    user_edited BOOLEAN DEFAULT FALSE,
    user_edited_at TIMESTAMP WITH TIME ZONE,
    
    -- Salesforce sync
    salesforce_synced BOOLEAN DEFAULT FALSE,
    salesforce_sync_at TIMESTAMP WITH TIME ZONE,
    salesforce_contact_id VARCHAR(50),
    salesforce_account_id VARCHAR(50),
    salesforce_opportunity_id VARCHAR(50),
    salesforce_task_id VARCHAR(50),
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_email_gmail_msg ON email_logs(gmail_message_id);
CREATE INDEX idx_email_thread ON email_logs(gmail_thread_id);
CREATE INDEX idx_email_user ON email_logs(user_id);
CREATE INDEX idx_email_status ON email_logs(status);
```

### Relationships
- `users` 1:N `oauth_connections` (CASCADE DELETE)
- `users` 1:N `email_logs` (CASCADE DELETE)

---

## 📊 Data Flow Mapping

### Email → Database → Salesforce

**Email Fetch:**
```
Gmail API → gmail_service.py → email_log entry → ai_service.py → update ai_extracted_data
```

**Email Approval:**
```
User clicks Approve → emails.py → salesforce_service.py → Salesforce API
                                → Update email_log with SF IDs
```

**Status Flow:**
```
fetch → pending_review → approve → approved (+ SF sync)
                       → reject → rejected
                       
failed → retry → pending_review/failed
rejected → restore → pending_review
```

