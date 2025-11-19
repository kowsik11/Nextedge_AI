# NextEdge 🚀

Welcome to NextEdge, your ultimate solution for seamless integration and intelligent automation! 🌟

NextEdge is designed to revolutionize how you connect your essential business tools, providing a powerful platform to streamline workflows, enhance productivity, and drive growth. Whether you're managing customer relationships with HubSpot, handling emails with Gmail, or organizing your sales pipeline, NextEdge brings everything together in one intuitive ecosystem.

## ✨ Key Features

- **Guided Workspace Onboarding**: Dedicated Gmail + HubSpot connection cards with live status, gating the workflow until both services are authenticated.
- **Live Inbox Preview**: Right-hand slide-over plus inbox explorer for new/processed/error tracking with quick links to Gmail and HubSpot records.
- **HubSpot Integration**: Effortlessly sync your CRM data and automate sales processes.
- **Gmail Integration**: Manage your email communications directly within NextEdge.
- **Zoho Integration**: Connect with Zoho services for comprehensive business management.
- **Intelligent Pipeline Management**: Optimize your sales pipeline with AI-driven insights.
- **Robust API**: Extend functionality and integrate with other tools using our powerful API.
- **Secure & Scalable**: Built with security and performance in mind, ready to grow with your business.

### Workspace Flow Highlights

1. **Connect Gmail & HubSpot** - cards progress through _Not Connected -> Connecting -> Connected_; the `Next` CTA stays disabled until both are green.
2. **Live notice slide-over** - after connecting, a right-side drawer shows last Gmail check time plus new/processed/error counts and a "View list" CTA.
3. **Inbox preview panel** - the left pane lists senders, subjects, previews, and attachment/link/image signals with filters + search, while the detail pane exposes compact previews with "Open in Gmail" / "Open in CRM note" links.
4. **Pipeline traceability** - every Gmail message now records processing status (new, processed, error) so Gemini + HubSpot runs are auditable from the UI.

## 🛠️ Technologies Used

- **Backend**: Python, FastAPI
- **Frontend**: React, TypeScript, Tailwind CSS
- **Database**: (To be specified, if applicable)
- **Authentication**: OAuth2

## 🚀 Getting Started

To get NextEdge up and running, follow these simple steps:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/saisharan0103/NextEdge.git
    cd NextEdge
    ```
2.  **Backend Setup**:
    ```bash
    cd backend
    python -m venv .venv
    .\.venv\Scripts\activate
    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8000
    ```
3.  **Frontend Setup**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## 🤝 Contributing

We welcome contributions from the community! If you'd like to contribute, please follow our contribution guidelines.

## 📄 License

This project is licensed under the MIT License.

---

Made with ❤️ by the NextEdge Team
