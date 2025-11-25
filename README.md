# NextEdge AI CRM 🚀

**Intelligent Email-to-CRM Automation Platform**

NextEdge is an advanced AI-powered CRM integration platform that seamlessly connects Gmail with Salesforce and HubSpot, using Google's Gemini AI to intelligently analyze, classify, and route emails to the appropriate CRM system. Built for sales teams, support agents, and businesses that want to automate their email-to-CRM workflow.

[![GitHub](https://img.shields.io/badge/GitHub-NextEdge_AI-blue?logo=github)](https://github.com/kowsik11/Nextedge_AI)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-blue?logo=react)](https://react.dev/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green?logo=supabase)](https://supabase.com/)

---

## 🌟 What NextEdge Does

NextEdge eliminates manual CRM data entry by:
- **Automatically syncing** emails from Gmail
- **Analyzing** email content using Google Gemini AI
- **Classifying** emails by intent (sales lead, support case, contact update, etc.)
- **Routing** emails to the right CRM (Salesforce or HubSpot)
- **Creating** appropriate CRM records (Leads, Cases, Contacts, Opportunities)
- **Maintaining** full email context and conversation threads in your CRM

**Result:** Your sales and support teams never miss a customer interaction, and every email is automatically logged where it belongs.

---

## ✨ Key Features

### 🤖 AI-Powered Email Intelligence
- **Gemini AI Analysis**: Advanced email classification using Google's Gemini 1.5 Flash
- **Intent Detection**: Identifies sales leads, support requests, general inquiries, and more
- **Urgency Detection**: Automatically prioritizes critical emails for immediate attention
- **Sentiment Analysis**: Understands customer tone and emotion in communications
- **Smart Routing**: Routes emails to the correct CRM system based on content and context

### 📧 Gmail Integration
- **OAuth 2.0 Authentication**: Secure, authorized access to Gmail accounts
- **Real-time Sync**: Automatic polling and webhook support for instant email processing
- **Full Email Access**: Reads email body, attachments, threads, and metadata
- **Thread Tracking**: Maintains conversation context across multiple emails
- **Label Support**: Sync specific Gmail folders and labels

### 🔷 Salesforce Integration
- **Multi-Object Support**: Creates Leads, Cases, Contacts, and Opportunities
- **Custom Fields**: Maps email data to custom Salesforce fields
- **Thread Management**: Updates existing Cases when replies are detected
- **Priority Mapping**: Sets Case priority based on AI urgency detection
- **Rich Descriptions**: Includes AI summary + full email content in records

### 🟠 HubSpot Integration
- **Contact Management**: Creates and updates HubSpot contacts automatically
- **Deal Tracking**: Generates deals from sales-related emails
- **Property Mapping**: Syncs email metadata to HubSpot properties
- **Activity Logging**: Records all email interactions in contact timeline
- **Custom Properties**: Supports custom HubSpot fields and pipelines

### 🎯 Workspace Management
- **Guided Onboarding**: Step-by-step connection flow for Gmail, Salesforce, and HubSpot
- **Live Status Dashboard**: Real-time connection status with visual indicators
- **OAuth Management**: Easy token refresh and re-authorization flows
- **Multi-Workspace**: Support for multiple organizations and teams
- **Access Control**: User authentication via Supabase Auth

### 📊 Email Pipeline Visibility
- **Processing Status**: Track emails as new, processing, processed, or error
- **Inbox Explorer**: Browse and search all synced emails
- **AI Insights Panel**: View classification results and confidence scores
- **Quick Actions**: Open emails in Gmail or view CRM records directly
- **Filters & Search**: Find emails by status, sender, date, or content

### 🔄 Background Processing
- **Automated Polling**: Continuous background sync every 5 minutes
- **Webhook Support**: Real-time processing via Gmail push notifications
- **Queue Management**: Reliable job processing with retry logic
- **Error Handling**: Graceful degradation with detailed error logging
- **Rate Limiting**: Respects API limits for Salesforce and HubSpot

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  - TypeScript, Tailwind CSS, Vite                           │
│  - OAuth Flows, Dashboard, Email Inbox UI                   │
└─────────────────┬───────────────────────────────────────────┘
                  │ REST API / WebSocket
┌─────────────────▼───────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  - Python 3.11+, Async/Await                                │
│  - OAuth Handlers, Email Processing, CRM Sync               │
└──┬────────┬─────────┬────────────┬──────────────────────────┘
   │        │         │            │
   ▼        ▼         ▼            ▼
┌──────┐ ┌──────┐ ┌────────┐ ┌──────────┐
│Gmail │ │Gemini│ │Salesf. │ │ HubSpot  │
│ API  │ │  AI  │ │  API   │ │   API    │
└──────┘ └──────┘ └────────┘ └──────────┘
   │                                    
   ▼                                    
┌─────────────────────────────────────┐
│       Supabase (PostgreSQL)         │
│  - Users, Workspaces, Emails        │
│  - OAuth Tokens, Processing Logs    │
└─────────────────────────────────────┘
```

### Technology Stack

#### Backend
- **Framework**: FastAPI 0.115+
- **Language**: Python 3.11+
- **Database ORM**: SQLAlchemy (async)
- **Authentication**: Supabase Auth + OAuth 2.0
- **AI**: Google Gemini 1.5 Flash API
- **External APIs**: Gmail, Salesforce, HubSpot, Zoho

#### Frontend
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS + shadcn/ui components
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Routing**: React Router v6

#### Database & Storage
- **Primary Database**: Supabase (PostgreSQL 15+)
- **Caching**: Redis (for rate limiting and queues)
- **File Storage**: Supabase Storage (email attachments)
- **Search**: PostgreSQL Full-Text Search

#### DevOps & Infrastructure
- **Deployment**: Vercel (Frontend), Railway/Render (Backend)
- **CI/CD**: GitHub Actions
- **Monitoring**: Sentry (error tracking)
- **Secrets Management**: Environment variables

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** and npm (for frontend)
- **Git** for version control
- **Supabase Account** ([free tier available](https://supabase.com))
- **Google Cloud Project** (for Gmail + Gemini APIs)
- **Salesforce Developer Account** (optional)
- **HubSpot Developer Account** (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/kowsik11/Nextedge_AI.git
cd Nextedge_AI
```

### 2. Backend Setup

#### Install Dependencies

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

#### Configure Environment Variables

Create `backend/.env` with the following:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Google OAuth & APIs
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Salesforce OAuth
SALESFORCE_CLIENT_ID=your-salesforce-client-id
SALESFORCE_CLIENT_SECRET=your-salesforce-client-secret
SALESFORCE_REDIRECT_URI=http://localhost:8000/auth/salesforce/callback

# HubSpot OAuth
HUBSPOT_CLIENT_ID=your-hubspot-client-id
HUBSPOT_CLIENT_SECRET=your-hubspot-client-secret
HUBSPOT_REDIRECT_URI=http://localhost:8000/auth/hubspot/callback

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:5173

# Server Configuration
ENVIRONMENT=development
```

#### Run Database Migrations

```bash
# Initialize Alembic (if needed)
alembic upgrade head
```

#### Start the Backend Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

📖 **API Documentation**: `http://localhost:8000/docs` (Swagger UI)

### 3. Frontend Setup

#### Install Dependencies

```bash
cd frontend
npm install
```

#### Configure Environment Variables

Create `frontend/.env`:

```env
VITE_BACKEND_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

#### Start the Development Server

```bash
npm run dev
```

Frontend will be available at `http://localhost:5173`

---

## 📂 Project Structure

```
NextEdge-dev/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── gmail.py              # Gmail API integration
│   │   │   ├── salesforce.py         # Salesforce API integration
│   │   │   ├── hubspot.py            # HubSpot API integration
│   │   │   ├── google_oauth.py       # Gmail OAuth flow
│   │   │   ├── oauth.py              # Generic OAuth utilities
│   │   │   ├── pipeline.py           # Email processing pipeline
│   │   │   ├── inbox.py              # Inbox management
│   │   │   ├── messages.py           # Email message handling
│   │   │   ├── gmail_poll.py         # Background polling worker
│   │   │   └── hubspot_contact_sync.py
│   │   ├── services/
│   │   │   ├── ai_service.py         # Gemini AI integration
│   │   │   ├── token_service.py      # OAuth token management
│   │   │   └── email_processor.py    # Email analysis logic
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── schemas/                  # Pydantic schemas
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── config.py                 # Settings and configuration
│   │   └── auth.py                   # Authentication middleware
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navigation.tsx
│   │   │   ├── ConnectionCard.tsx
│   │   │   ├── EmailList.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Workspace.tsx
│   │   │   ├── Inbox.tsx
│   │   │   └── Settings.tsx
│   │   ├── lib/
│   │   │   ├── api.ts               # API client
│   │   │   ├── supabase.ts          # Supabase client
│   │   │   └── types.ts             # TypeScript types
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── .env
│
├── docs/                             # Documentation
│   ├── API_integration.md
│   ├── Salesforce_integration.md
│   └── FLOWS.md
│
├── ISSUES_RESOLVED.md                # Complete bug fix log
├── EXCLUDED_FILES_SUMMARY.md         # Git exclusion list
├── salesforce_integration_plan.md
└── README.md
```

---

## 🔌 API Endpoints

### Authentication
- `GET /auth/google` - Initiate Gmail OAuth
- `GET /auth/google/callback` - Gmail OAuth callback
- `GET /auth/salesforce` - Initiate Salesforce OAuth
- `GET /auth/salesforce/callback` - Salesforce OAuth callback
- `GET /auth/hubspot` - Initiate HubSpot OAuth
- `GET /auth/hubspot/callback` - HubSpot OAuth callback

### Gmail
- `GET /gmail/messages` - Fetch Gmail messages
- `POST /gmail/sync` - Trigger manual sync
- `GET /gmail/status` - Get Gmail connection status

### Salesforce
- `POST /salesforce/sync` - Sync email to Salesforce
- `GET /salesforce/status` - Get connection status
- `POST /salesforce/create-lead` - Create Salesforce Lead
- `POST /salesforce/create-case` - Create Salesforce Case

### HubSpot
- `POST /hubspot/sync` - Sync email to HubSpot
- `GET /hubspot/status` - Get connection status
- `POST /hubspot/create-contact` - Create HubSpot contact

### Email Pipeline
- `GET /pipeline/emails` - List processed emails
- `GET /pipeline/status` - Processing statistics
- `POST /pipeline/reprocess/{email_id}` - Reprocess failed email

### Inbox
- `GET /inbox/messages` - Get inbox messages
- `GET /inbox/message/{id}` - Get message details
- `PUT /inbox/message/{id}/status` - Update message status

---

## 🎯 Usage Workflow

### 1. User Onboarding
1. User signs up via Supabase Auth
2. Creates a workspace
3. Connects Gmail via OAuth
4. Connects Salesforce and/or HubSpot (optional)

### 2. Email Processing Flow
```
Gmail → Fetch Email → Gemini AI Analysis → Classification Decision
                                                    ↓
                                    ┌───────────────┴───────────────┐
                                    ▼                               ▼
                            Salesforce Sync                  HubSpot Sync
                         (Lead/Case/Contact)              (Contact/Deal)
```

### 3. AI Classification Logic
- **Lead**: Sales inquiries, demo requests, pricing questions
- **Case**: Support issues, bug reports, complaints
- **Contact**: General information, follow-ups, networking
- **Opportunity**: Active deals, contract discussions
- **None**: Spam, newsletters, internal communications

### 4. CRM Record Creation
- Email body + AI summary included in description
- Metadata fields populated (sender, subject, urgency)
- Thread tracking for conversation continuity
- Attachments linked (where supported)

---

## 🧪 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

### Code Quality

```bash
# Backend linting
ruff check .
black .

# Frontend linting
npm run lint
npm run type-check
```

### Building for Production

```bash
# Backend
pip install -r requirements.txt

# Frontend
npm run build
```

---

## 🔒 Security & Privacy

- **OAuth 2.0**: Secure authorization for all integrations
- **Token Encryption**: Sensitive tokens stored encrypted in database
- **CORS Protection**: Restricted origins for API access
- **Rate Limiting**: Prevents API abuse
- **Data Isolation**: Multi-tenant architecture with workspace separation
- **No Password Storage**: Uses Supabase Auth for user management
- **.gitignore Protection**: Sensitive files excluded from repository

**Files Never Committed:**
- `*.env` files
- `*tokens.json` files
- `credentials.json`
- Database backups
- API keys or secrets

See `EXCLUDED_FILES_SUMMARY.md` for complete exclusion list.

---

## 📝 Documentation

- **[API Integration Guide](docs/API_integration.md)** - Comprehensive API documentation
- **[Salesforce Setup](docs/Salesforce_integration.md)** - Salesforce-specific configuration
- **[Workflow Diagrams](docs/FLOWS.md)** - Visual workflow explanations
- **[Issues Resolved](ISSUES_RESOLVED.md)** - Complete bug fix log (50+ issues)
- **[Salesforce Integration Plan](salesforce_integration_plan.md)** - Implementation roadmap

---

## 🚦 Deployment

### Backend Deployment (Railway/Render)
1. Connect GitHub repository
2. Set environment variables
3. Deploy main branch
4. Configure custom domain (optional)

### Frontend Deployment (Vercel)
1. Import GitHub repository
2. Configure build settings:
   - Build Command: `npm run build`
   - Output Directory: `dist`
3. Add environment variables
4. Deploy

### Database (Supabase)
- No deployment needed (managed service)
- Configure Row Level Security (RLS) policies
- Set up database backups

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and commit: `git commit -m 'Add amazing feature'`
4. **Push to your fork**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Contribution Guidelines
- Follow existing code style (Black for Python, ESLint for TypeScript)
- Write tests for new features
- Update documentation as needed
- Keep commits atomic and well-described

---

## 🐛 Known Issues & Troubleshooting

### Common Issues

**OAuth Redirect Mismatch**
- Ensure redirect URIs in Google/Salesforce/HubSpot consoles match your `.env` configuration
- Use exact URLs including protocol (http/https)

**Database Connection Errors**
- Verify Supabase credentials in `.env`
- Check if Supabase project is active
- Ensure connection pool isn't exhausted

**CORS Errors**
- Confirm `FRONTEND_URL` in backend `.env` matches your frontend URL
- Check CORS middleware configuration in `main.py`

**Token Expiration**
- Tokens refresh automatically; if issues persist, reconnect OAuth
- Check token expiry handling in `token_service.py`

For more issues and solutions, see **[ISSUES_RESOLVED.md](ISSUES_RESOLVED.md)**

---

## 📊 Current Status

- ✅ Gmail Integration (OAuth + Sync)
- ✅ Gemini AI Email Classification
- ✅ Salesforce Integration (Leads, Cases, Contacts)
- ✅ HubSpot Integration (Contacts, Deals)
- ✅ React Frontend with Dashboard
- ✅ Background Email Processing
- ✅ Multi-workspace Support
- ✅ Real-time Status Updates
- 🚧 Zoho Integration (in progress)
- 🚧 Mobile App (planned)

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**NextEdge AI Team**
- Built with ❤️ for sales and support teams everywhere
- Powered by Google Gemini AI

---

## 🔗 Links

- **Repository**: [github.com/kowsik11/Nextedge_AI](https://github.com/kowsik11/Nextedge_AI)
- **Issues**: [Report a bug or request a feature](https://github.com/kowsik11/Nextedge_AI/issues)
- **Documentation**: See `/docs` directory
- **API Docs** (local): `http://localhost:8000/docs`

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **React** - Frontend library
- **Supabase** - Backend-as-a-Service
- **Google Gemini AI** - Advanced email analysis
- **Salesforce** - CRM platform
- **HubSpot** - CRM & Marketing platform

---

**Last Updated**: 2025-11-25
**Version**: 1.0.0

*NextEdge AI - Intelligent Email-to-CRM Automation* 🚀
