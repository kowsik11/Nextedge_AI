# PART 4: INTEGRATIONS & AI LAYER

## 🔵 GMAIL INTEGRATION

### OAuth Configuration
**Client ID:** From Google Cloud Console → OAuth credentials  
**Client Secret:** From Google Cloud Console  
**Scopes:**
- `https://www.googleapis.com/auth/gmail.readonly` - Read sent emails
- `https://www.googleapis.com/auth/userinfo.email` - User email
- `https://www.googleapis.com/auth/userinfo.profile` - User profile

**Redirect URI:** `http://localhost:8000/auth/gmail/callback`

### Gmail API Endpoints Used
1. **Users.messages.list** - List sent emails
   - Query: `in:sent`
   - Max results: 10 (default)
   - Returns: message IDs + next page token

2. **Users.messages.get** - Get full email details
   - Format: `full` (includes headers + body)
   - Parses: headers, body (plain text/HTML), attachments metadata

### Email Parsing Logic
**Headers extracted:**
- Subject
- From (with email extraction: "Name <email>" → "email")
- To
- CC
- Date (parsed to timezone-aware datetime)

**Body extraction:**
- Multipart messages: Try text/plain → fallback to text/html
- HTML → Plain text using BeautifulSoup
- Base64 URL-safe decoding

### Token Management
- **Access Token:** Short-lived (1 hour)
- **Refresh Token:** Long-lived (stored in DB)
- **Auto-refresh:** `google.auth` library handles automatically
- **Storage:** `oauth_connections` table

### Email Filtering (Pre-AI)
Not implemented yet, but designed for:
- Skip internal emails (same domain)
- Skip personal domains (gmail.com, yahoo.com)
- Skip auto-replies ("out of office")

### Gmail Push Notifications
**Status:** Not implemented (manual fetch only)  
**Future:** Google Cloud Pub/Sub + Gmail Watch API

---

## 🟠 SALESFORCE INTEGRATION

### OAuth Configuration
**Consumer Key:** From Salesforce Connected App  
**Consumer Secret:** From Salesforce Connected App  
**Scopes:**
- `api` - Salesforce API access
- `refresh_token` - Offline access

**Redirect URI:** `http://localhost:8000/auth/salesforce/callback`  
**Login URL:** `https://login.salesforce.com` (production orgs)  
**Alternative:** `https://test.salesforce.com` (sandbox orgs)

### Salesforce API Version
**API Version:** 58.0  
**Library:** `simple-salesforce` (Python SDK)

### Token Management
- **Access Token:** 2-hour expiry
- **Refresh Token:** Permanent (until revoked)
- **Auto-refresh:** Custom logic in `salesforce_service.py`
- **Storage:** `oauth_connections` table + `instance_url`

### Salesforce Objects & Field Mapping

#### 1. Account (Company)
**Search Logic:**
1. Search by `Website` field (contains domain)
2. Fallback: Search by `Name` (exact match)
3. If not found: Create new

**Fields Created:**
```python
{
  'Name': company_name,               # REQUIRED
  'Website': domain,                  # Optional
  'Industry': industry,               # Optional
  'Description': f"Company size: {size}\n\nAuto-created by AutoCRM on {date}"
}
```

**SOQL Query:**
```sql
SELECT Id, Name FROM Account WHERE Website LIKE '%{domain}%' LIMIT 1
SELECT Id, Name FROM Account WHERE Name = '{company_name}' LIMIT 1
```

---

#### 2. Contact (Person)
**Search Logic:**
1. Search by `Email` (exact match)
2. If found: Update `AccountId` if different
3. If not found: Create new

**Fields Created:**
```python
{
  'Email': email,                     # REQUIRED
  'LastName': last_name,             # REQUIRED (Salesforce requirement)
  'FirstName': first_name,           # Optional
  'AccountId': account_id,           # REQUIRED (link to Account)
  'Title': title,                    # Optional
  'Phone': phone                     # Optional
}
```

**Name Parsing:**
- "John Doe" → FirstName: "John", LastName: "Doe"
- "Smith" → LastName: "Smith"
- No name → LastName: email prefix (before @)

**SOQL Query:**
```sql
SELECT Id, Name, AccountId FROM Contact WHERE Email = '{email}' LIMIT 1
```

---

#### 3. Opportunity (Deal)
**Creation Logic:**
- Only create if `opportunity.should_create = true` (from AI)
- Check for existing open opportunity on same Account
- If exists: Return existing (avoid duplicates)
- If not: Create new

**Fields Created:**
```python
{
  'Name': f"{product} - {email_subject[:50]}",  # REQUIRED
  'AccountId': account_id,                      # REQUIRED
  'StageName': salesforce_stage,                # REQUIRED
  'CloseDate': close_date,                      # REQUIRED (default: +90 days)
  'LeadSource': 'AutoCRM',
  'Amount': amount,                             # Optional
  'Description': f"Product Interest: {product}\nCompetitors: {competitors}\n\nAuto-created..."
}
```

**Stage Mapping (AI → Salesforce):**
```python
{
  'Prospecting': 'Prospecting',
  'Qualification': 'Qualification',
  'Demo': 'Needs Analysis',
  'Proposal': 'Proposal/Price Quote',
  'Negotiation': 'Negotiation/Review',
  'Closed Won': 'Closed Won',
  'Closed Lost': 'Closed Lost'
}
```

**SOQL Query:**
```sql
SELECT Id, Name, StageName FROM Opportunity 
WHERE AccountId = '{account_id}' AND IsClosed = false 
ORDER BY CreatedDate DESC LIMIT 1
```

---

#### 4. Task (Email Activity Log)
**Always Created** (every approved email)

**Fields Created:**
```python
{
  'Subject': f"Email: {email_subject}",     # REQUIRED
  'Status': 'Completed',                    # Email already sent
  'ActivityDate': sent_date,                # Email sent date
  'TaskSubtype': 'Email',
  'WhoId': contact_id,                      # Link to Contact
  'WhatId': opportunity_id or account_id,   # Link to Opportunity or Account
  'Priority': 'Normal',
  'Description': f"{activity_summary}\n\nNext Steps:\n{next_steps}\n\nLogged by AutoCRM..."
}
```

**Link Logic:**
- `WhoId` → Contact (person)
- `WhatId` → Opportunity (if exists) OR Account (fallback)

---

#### 5. OpportunityContactRole (Link Contact to Opportunity)
**Created when Opportunity is created**

**Fields:**
```python
{
  'OpportunityId': opportunity_id,
  'ContactId': contact_id,
  'IsPrimary': True,
  'Role': 'Decision Maker'
}
```

---

### Salesforce Sync Flow (End-to-End)

```
User clicks "Approve" on email
         ↓
1. Find or Create Account
   - Search by domain → name
   - If not found: Create
   - Returns: account_id
         ↓
2. Find or Create Contact
   - Search by email
   - If found: Update AccountId
   - If not found: Create
   - Returns: contact_id
         ↓
3. Find or Create Opportunity (Conditional)
   - Check: opportunity.should_create = true?
   - Search for existing open opp on Account
   - If not found: Create
   - Returns: opportunity_id (or None)
         ↓
4. Create Task
   - Link to Contact (WhoId)
   - Link to Opportunity or Account (WhatId)
   - Returns: task_id
         ↓
5. Link Contact to Opportunity (if opp created)
   - Create OpportunityContactRole
         ↓
6. Update email_log with Salesforce IDs
   - salesforce_account_id
   - salesforce_contact_id
   - salesforce_opportunity_id
   - salesforce_task_id
         ↓
7. Set status: "approved"
```

### Error Handling
**Common Errors:**
1. **Authentication Failed** → Auto-refresh token, retry once
2. **Required Field Missing** → Return error (no defaults)
3. **Duplicate Detection Rules** → Respect SF rules, return error
4. **Permission Denied** → Return error (user must grant permissions)
5. **API Limit Reached** → Return error (queue for later)

**Error Logging:**
- Stored in `email_log.error_message`
- Status set to "failed"
- `retry_count` incremented

---

## 🤖 AI LAYER (Azure OpenAI)

### Model Configuration
**Provider:** Azure OpenAI  
**Deployment:** `ai-coe-gpt4o:analyze`  
**Model:** GPT-4o  
**API Version:** `2023-05-15`

**Azure Endpoint Format:**
```
https://{ENVIRONMENT_URL}/api/v1/ai/{PROJECT_NAME}/OAI
```

### API Parameters
```python
{
  "model": "ai-coe-gpt4o:analyze",
  "messages": [
    {"role": "system", "content": "You are a CRM data extraction assistant..."},
    {"role": "user", "content": "{extraction_prompt}"}
  ],
  "max_tokens": 4000,
  "temperature": 0.0  # Deterministic for structured extraction
}
```

### Prompt Engineering

**Input Data Passed to Model:**
- From email address
- To email address
- Subject
- Body (plain text)
- Sent date

**Prompt Structure:**
1. Role definition (CRM assistant for B2B SaaS)
2. Email details
3. Extraction task with JSON schema
4. Rules & guidelines
5. Example JSON output

**Key Rules in Prompt:**
- Extract ONLY explicitly mentioned information
- Do NOT make assumptions
- Use null for missing data
- `is_prospect_email`: false for personal/internal/automated emails
- `opportunity.should_create`: only true for real deal discussion (pricing, demo, proposal)

### AI Output Format

```json
{
  "is_prospect_email": true,
  "contact": {
    "name": "John Smith",
    "email": "john@acme.com",
    "title": "VP of Sales",
    "phone": "+1-555-1234"
  },
  "account": {
    "company_name": "Acme Corporation",
    "domain": "acme.com",
    "industry": "Technology",
    "size": "500 employees"
  },
  "opportunity": {
    "should_create": true,
    "stage": "Proposal",
    "amount": 50000,
    "close_date": "2025-12-31",
    "product": "Enterprise Plan",
    "competitors": ["Competitor A", "Competitor B"]
  },
  "activity": {
    "summary": "Sent Q4 pricing proposal for Enterprise plan. Discussed implementation timeline and contract terms.",
    "next_steps": "Follow up next week to schedule final demo",
    "sentiment": "positive"
  },
  "follow_up": {
    "required": true,
    "date": "2025-11-29",
    "task_description": "Follow up on pricing proposal"
  },
  "confidence": {
    "overall": 0.85,
    "contact": 0.95,
    "opportunity": 0.75
  }
}
```

### Response Parsing Logic

1. **Clean Response:**
   - Remove markdown code blocks (```json, ```)
   - Fix unquoted sentiment values
   - Trim whitespace

2. **Parse JSON:**
   - Use `json.loads()`
   - Handle `JSONDecodeError`

3. **Validate Required Fields:**
   - Check for: `is_prospect_email`, `contact`, `account`, `opportunity`, `activity`, `follow_up`, `confidence`
   - Provide defaults if missing

4. **Sanitize Confidence Scores:**
   - Clamp to 0.0-1.0 range

5. **Check Truncation:**
   - If `finish_reason = "length"` → Error (response truncated)

### Confidence Calculation

**Hybrid Confidence Score:**
```python
ai_confidence = extracted_data['confidence']['overall']  # From AI model
field_completeness = calculate_field_completeness(data)  # Our calculation

final_confidence = (ai_confidence * 0.7) + (field_completeness * 0.3)
```

**Field Completeness Scoring:**
- Start: 1.0
- Missing contact.name: -0.15
- Missing contact.email: -0.15
- Missing contact.title: -0.05
- Missing account.company_name: -0.15
- Missing account.domain: -0.10
- Missing activity.summary: -0.10
- Missing activity.next_steps: -0.05
- If opportunity.should_create = true:
  - Missing opportunity.stage: -0.10
  - Missing amount AND product: -0.05

**Result:** 0.0-1.0 score

### Auto-Classification Logic

**`is_prospect_email` determines status:**
- `true` → Status: `pending_review` (user must approve)
- `false` → Status: `rejected` (auto-rejected, non-prospect)

**Examples of non-prospect emails:**
- Personal emails ("dinner plans")
- Internal emails (to colleagues)
- Automated replies ("out of office")
- Newsletters, notifications

### Cost Estimation
- **Input:** ~500-1000 tokens per email (subject + body)
- **Output:** ~500-800 tokens (JSON response)
- **Total:** ~1000-1800 tokens per email
- **Cost:** ~$0.10-0.15 per email (GPT-4o pricing)

### Error Handling

**AI Extraction Errors:**
1. **JSON Parse Error** → Status: `failed`, log error
2. **Response Truncated** → Status: `failed`, log "increase max_tokens"
3. **API Timeout** → Retry with exponential backoff (not implemented)
4. **Invalid API Key** → Status: `failed`, log "check credentials"

**Retry Logic:**
- User can manually retry failed emails: `POST /emails/{id}/retry`
- Increments `retry_count`
- Re-runs AI extraction

---

## 🔗 Integration Dependencies

### Gmail Dependencies
```python
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
```

### Salesforce Dependencies
```python
simple-salesforce  # Salesforce API wrapper
httpx  # HTTP client for token refresh
```

### AI Dependencies
```python
openai  # Azure OpenAI SDK
```

### Other
```python
beautifulsoup4, bs4  # HTML parsing (email bodies)
```

---

## 🔐 Security Considerations

### Token Storage
- **Access Tokens:** Encrypted in DB (not implemented)
- **Refresh Tokens:** Stored in DB (plain text - TODO: encrypt)
- **JWT Secret:** In environment variable (not in code)

### Data Privacy
- Email body stored in plain text in DB
- AI sends email content to Azure OpenAI
- User can delete data (CASCADE DELETE on users)

### API Rate Limits
- **Gmail:** 250 quota units per user per second
- **Salesforce:** 5,000-25,000 API calls per day (depends on edition)
- **Azure OpenAI:** Tokens per minute (TPM) limit

**Current:** No rate limit handling (TODO)

