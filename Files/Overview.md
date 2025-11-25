# PART 1: PROJECT OVERVIEW & ARCHITECTURE

## 📋 PROJECT SUMMARY

**Project Name:** AutoCRM  
**Purpose:** AI-powered email monitoring that automatically logs sales activities in Salesforce for SaaS Account Executives  
**Status:** ✅ MVP Complete (Phases 1-4 done)

### What It Does
- Fetches sent emails from Gmail
- Uses Azure OpenAI (GPT-4) to extract CRM data
- Allows user to review/edit AI extractions
- Syncs approved emails to Salesforce (Account, Contact, Opportunity, Task)

### What It's NOT
- ❌ Not a CRM replacement (enhances Salesforce)
- ❌ Not for received emails (sent only)
- ❌ Not multi-user (single user MVP)

---

## 🏗️ TECH STACK

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL with JSONB support
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT (python-jose)

### Frontend
- **Framework:** React 18.3.1
- **Build Tool:** Vite 5.4.1
- **Router:** React Router DOM 6.26.0
- **HTTP Client:** Axios 1.7.2

### Integrations
- **Gmail:** Google OAuth2 + Gmail API
- **Salesforce:** Salesforce OAuth2 + REST API (simple-salesforce)
- **AI:** Azure OpenAI (GPT-4o)

### Infrastructure
- **Development:** localhost (Backend: 8000, Frontend: 3000)
- **Not yet deployed**

---

## 📁 COMPLETE REPOSITORY STRUCTURE

```
NewProjectASK/
├── autocrm/                          # Main application folder
│   ├── backend/                      # FastAPI backend
│   │   ├── alembic/                  # Database migrations
│   │   │   ├── versions/
│   │   │   │   ├── 5ef474bb3e23_initial_tables_users_and_oauth_.py
│   │   │   │   └── 72cc62aa9f4b_add_email_logs_table.py
│   │   │   ├── env.py               # Alembic environment config
│   │   │   └── script.py.mako       # Migration template
│   │   ├── app/                      # Main application code
│   │   │   ├── api/                  # API endpoints
│   │   │   │   ├── auth.py          # Google OAuth login
│   │   │   │   ├── gmail.py         # Gmail OAuth & status
│   │   │   │   ├── salesforce.py    # Salesforce OAuth & status
│   │   │   │   └── emails.py        # Email management (fetch, approve, reject)
│   │   │   ├── models/               # Database models
│   │   │   │   ├── user.py          # User model
│   │   │   │   ├── oauth_connection.py  # OAuth tokens
│   │   │   │   └── email_log.py     # Email logs & AI data
│   │   │   ├── services/             # Business logic
│   │   │   │   ├── gmail_service.py     # Gmail API integration
│   │   │   │   ├── ai_service.py        # Azure OpenAI extraction
│   │   │   │   └── salesforce_service.py  # Salesforce sync
│   │   │   ├── utils/                # Utilities
│   │   │   │   ├── jwt_handler.py   # JWT token creation/verification
│   │   │   │   └── dependencies.py  # FastAPI dependencies
│   │   │   ├── config.py             # Settings (loads from .env)
│   │   │   ├── database.py           # SQLAlchemy setup
│   │   │   └── main.py               # FastAPI app entry point
│   │   ├── requirements.txt          # Python dependencies
│   │   ├── alembic.ini              # Alembic configuration
│   │   ├── .env                     # Environment variables (NOT in git)
│   │   └── venv/                    # Python virtual environment
│   │
│   └── frontend/                     # React frontend
│       ├── src/
│       │   ├── components/           # Reusable components
│       │   │   ├── ProtectedRoute.jsx   # Auth guard
│       │   │   ├── StatusBadge.jsx      # Email status display
│       │   │   ├── EmailCard.jsx        # Email list item
│       │   │   ├── EmailDetail.jsx      # Email detail sidebar
│       │   │   └── EmailDetail.css
│       │   ├── pages/                # Page components
│       │   │   ├── Login.jsx            # Login page
│       │   │   ├── AuthCallback.jsx     # OAuth redirect handler
│       │   │   ├── Dashboard.jsx        # Main dashboard
│       │   │   ├── EmailList.jsx        # Email list (all/pending/approved/etc)
│       │   │   └── [corresponding .css files]
│       │   ├── services/
│       │   │   └── api.js           # API client & service methods
│       │   ├── App.jsx              # Main app component (routes)
│       │   ├── main.jsx             # React entry point
│       │   └── index.css            # Global styles
│       ├── index.html               # HTML template
│       ├── package.json             # NPM dependencies
│       ├── vite.config.js           # Vite configuration
│       └── node_modules/            # NPM packages
│
├── Docs/                             # Documentation
│   ├── SETUP_GUIDE.md               # Service setup instructions
│   ├── IMPLEMENTATION_ROADMAP.md    # Phase-by-phase guide
│   ├── QUICK_REFERENCE.md           # Commands & debugging
│   └── [other docs]
│
├── Details/                          # Technical handover (THIS FOLDER)
│   ├── PART1_OVERVIEW_ARCHITECTURE.md
│   ├── PART2_CODEBASE_COMPONENTS.md
│   ├── PART3_API_DATABASE.md
│   ├── PART4_INTEGRATIONS_AI.md
│   └── PART5_FLOWS_DEPLOYMENT.md
│
├── PROJECT_CONTEXT.md               # Master planning document
└── START_HERE.md                    # Onboarding guide
```

---

## 🎯 ARCHITECTURE OVERVIEW

### High-Level Data Flow

```
User sends email → Gmail → User clicks "Fetch Emails" → Backend
                                                            ↓
                                    Gmail API fetches sent emails
                                                            ↓
                                    Azure OpenAI extracts CRM data
                                                            ↓
                                    Stored in PostgreSQL (pending_review)
                                                            ↓
                                    User reviews in UI → Approves/Rejects
                                                            ↓
                                    If Approved → Salesforce Sync
                                                            ↓
                            Account, Contact, Opportunity, Task created
                                                            ↓
                                    Status: "approved" (logged)
```

### Component Architecture

**3-Tier Architecture:**
1. **Frontend (React)** - User interface
2. **Backend (FastAPI)** - Business logic & API
3. **External Services** - Gmail, Salesforce, Azure OpenAI

**Backend Layers:**
- **API Layer** (`app/api/`) - HTTP endpoints
- **Service Layer** (`app/services/`) - Business logic
- **Data Layer** (`app/models/`) - Database models
- **Utils Layer** (`app/utils/`) - Shared utilities

---

## 🗄️ DATABASE SCHEMA

### Tables

**1. users**
- Stores user accounts (Google OAuth)
- Fields: id, google_id, email, name, picture, company_name, company_domain

**2. oauth_connections**
- Stores OAuth tokens for Gmail & Salesforce
- Fields: id, user_id, provider, access_token, refresh_token, expires_at, instance_url

**3. email_logs**
- Stores all fetched emails + AI extraction + Salesforce IDs
- Fields: id, user_id, gmail_message_id, subject, body, ai_extracted_data (JSONB), ai_confidence, status, salesforce_*_id

---

## 🔐 AUTHENTICATION FLOW

### User Login (Google OAuth)
```
1. User clicks "Sign in with Google" → /auth/google
2. Redirect to Google OAuth consent screen
3. Google redirects back → /auth/google/callback
4. Backend exchanges code for tokens
5. Backend creates/updates User in DB
6. Backend generates JWT token
7. Frontend stores JWT in localStorage
8. All API requests include: Authorization: Bearer <token>
```

### Gmail Connection
```
1. User clicks "Connect Gmail" → /auth/gmail?user_id={id}
2. Redirect to Google OAuth (scope: gmail.readonly)
3. Google redirects back → /auth/gmail/callback
4. Backend stores tokens in oauth_connections table
5. Status: connected
```

### Salesforce Connection
```
1. User clicks "Connect Salesforce" → /auth/salesforce?user_id={id}
2. Redirect to Salesforce OAuth (scope: api, refresh_token)
3. Salesforce redirects back → /auth/salesforce/callback
4. Backend stores tokens + instance_url in oauth_connections
5. Status: connected
```

---

## 🔄 STATE MANAGEMENT

### Email States
- **pending_review** - Fetched, AI extracted, waiting for user approval
- **approved** - User approved, synced to Salesforce successfully
- **rejected** - User rejected, will not sync to Salesforce
- **failed** - AI extraction or Salesforce sync failed
- **logged** (same as approved) - Successfully synced

### State Transitions
```
Fetch → pending_review → Approve → approved (Salesforce sync)
                       → Reject → rejected
                       
Fetch → failed (AI error) → Retry → pending_review/failed

rejected → Restore → pending_review
```

---

## 📊 KEY DESIGN DECISIONS

1. **No Polling** - Manual fetch only (no Gmail push notifications implemented yet)
2. **Synchronous AI** - AI extraction runs synchronously during fetch (not background)
3. **Manual Approval** - User must approve before Salesforce sync (trust building)
4. **Skip Leads** - Directly create Account → Contact → Opportunity (no Lead object)
5. **Find-or-Create** - Search existing records before creating new ones
6. **Auto-Reject Non-Prospects** - AI classifies emails; non-prospects auto-rejected
7. **JSONB Storage** - AI extraction stored as JSONB for flexibility

---

## 🎨 UI STRUCTURE

### Pages
1. **Login** - Google OAuth login
2. **Dashboard** - Overview, stats, connection status
3. **Email Lists** - All/Pending/Approved/Rejected/Failed emails
4. **Email Detail Sidebar** - View email + AI extraction + Salesforce preview

### User Workflow
```
Dashboard → View Stats → Connect Gmail/Salesforce
         → Fetch Emails → View Pending Emails
         → Click Email → Review AI Data → Edit if needed
         → Approve → Salesforce Sync → View in "Approved"
```

---

## 🚀 DEPLOYMENT STATUS

**Current:** Development only (localhost)  
**Future:** Railway/Render for deployment

### Environment Variables Required
See `.env` file structure in PART 5.

