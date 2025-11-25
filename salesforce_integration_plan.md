# Salesforce CRM Integration Plan for NextEdge

## Executive Summary
- Integrate Salesforce CRM alongside existing HubSpot integration with full support for all 7 standard Salesforce objects.
- Maintain parallel OAuth connection management and independent routing so users can target HubSpot, Salesforce, or both.
- Add UI affordances for connecting Salesforce and routing emails; persist Salesforce metadata in Supabase without altering HubSpot tables.

## Salesforce Objects Coverage
- Account (Companies equivalent)
- Contact (Contacts)
- Lead (prospect before qualification; converts to Contact/Account)
- Opportunity (Deals equivalent)
- Case (Tickets equivalent)
- Campaign (Marketing initiative)
- Order (Orders equivalent)

## Environment & OAuth Setup
1. Create Salesforce Developer Account at https://developer.salesforce.com/signup and capture instance URL.
2. Configure Connected App:
   - Name: NextEdge CRM; API name auto; contact email set.
   - Enable OAuth with redirect URIs: `http://localhost:8000/api/salesforce/callback` and production domain equivalent.
   - Scopes: `api`, `refresh_token`, `web`, `openid`; require secret for web/refresh flows; relax IP restrictions.
   - Copy Consumer Key/Secret after propagation.
3. Environment variables:
   - `SALESFORCE_CLIENT_ID`, `SALESFORCE_CLIENT_SECRET`, `SALESFORCE_REDIRECT_URI`
   - `SALESFORCE_AUTH_URL`, `SALESFORCE_TOKEN_URL`, `SALESFORCE_API_VERSION`
   - `SALESFORCE_SCOPES="api refresh_token web openid"`

## Database (Supabase)
- New table `public.salesforce_connections` to store per-user Salesforce connection metadata.
- New table `public.gmail_message_salesforce_meta` to track Salesforce routing metadata for Gmail messages (all 7 object IDs plus AI decision fields).
- Extend `authentication.gmail_messages` with Salesforce columns (object type and IDs for all 7 objects + task).
- Add indexes for Salesforce columns.
- Recreate `public.gmail_messages` view to include Salesforce fields alongside HubSpot.
- Add helper function `public.get_message_crm_status(msg_id uuid)` returning JSON with HubSpot and Salesforce object status.
- OAuth tokens remain in existing `public.oauth_connections` with `provider='salesforce'`.

## Backend Architecture
- New router: `backend/app/routers/salesforce.py` for OAuth endpoints/status/test.
- New services:
  - `salesforce_oauth.py`: auth URL generation, code exchange, token refresh, token retrieval.
  - `salesforce_client.py`: REST client covering create/search/update/upsert for Contact, Account, Opportunity, Lead (incl. convert), Case, Campaign, Order, Task.
  - `crm_router.py`: AI-driven dual CRM routing logic (HubSpot + Salesforce).
- Update `backend/app/storage/supabase_token_store.py` to add `salesforce_token_store`.
- Update `backend/app/config.py` with Salesforce settings (client ID/secret, redirect URI, auth/token URLs, API version, scopes).

## Frontend Updates
- `frontend/src/pages/Home.tsx`:
  - Add Salesforce connection status fetch and a connection card mirroring HubSpot.
  - Add “☁️ Salesforce” button next to existing HubSpot button in inbox preview for routing emails.
  - Handler `routeToSalesforce` posts to `/api/salesforce/route-email` with user token; refresh inbox afterward.
  - Minor layout: decrease width allocated to Gmail/HubSpot blocks to fit Salesforce button while keeping style consistent; Salesforce button uses blue gradient styling.

## AI Routing
- Extend AI output to include `target_crm: ["hubspot", "salesforce"]` to allow dual routing without changing extraction logic.
- Continue returning primary object, confidence, and reasoning; route per selected CRM(s).

## Testing & Verification
1. Salesforce setup: create developer account + connected app; populate env vars.
2. Database: run updated `schema.sql`; verify new tables/columns/view/function.
3. Backend: test OAuth flow; CRUD for Contact/Account/Opportunity/Lead (convert), Case, Campaign, Order, Task.
4. Frontend: verify Salesforce connection card and button; OAuth connect/disconnect; email routing to Salesforce.
5. End-to-end: route an email to HubSpot then Salesforce; confirm records in both CRMs independently.

## Next Steps
- Confirm plan, create connected app, and add credentials to environment.
- Apply Supabase migration, implement backend services/routes, wire frontend UI, then run E2E tests.

## Reference: Salesforce Dev Org Details
- Username: saisharandomakonda968@agentforce.com
- Instance URL: https://orgfarm-f07facf154-dev-ed.develop.my.salesforce.com
