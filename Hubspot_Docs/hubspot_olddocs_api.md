# HubSpot API Structured Reference

This file reorganizes the provided HubSpot API material so that every endpoint explicitly lists its path, method, headers, and payload expectations exactly as documented. No new details have been introduced.

## 1. Automation API | Custom Workflow Actions

Custom workflow actions use the v2 `X-HubSpot-Signature` when HubSpot calls your `actionUrl`. Requests to manage custom workflow actions must be authenticated with OAuth or private app access tokens.

### 1.1 Complete a Blocked Custom Action Execution
- **Endpoint**: `/callbacks/{callbackId}/complete`
- **Method**: Not specified in the source text.
- **Headers**: Not specified.
- **Payload**:
  ```json
  {
    "outputFields": {
      "hs_execution_state": "SUCCESS"
    }
  }
  ```
- **Fields**:
  | Field | Description |
  | --- | --- |
  | `hs_execution_state` | Required. Set to `SUCCESS` when the custom action completed properly or `FAIL_CONTINUE` if the workflow should keep going despite an error. |

To block execution in the first place your custom action response must include:
```json
{
  "outputFields": {
    "hs_execution_state": "BLOCK",
    "hs_expiration_duration": "P1WT1H"
  }
}
```
`hs_expiration_duration` follows ISO 8601 duration syntax. If omitted, HubSpot uses a default expiration of 1 week.
## 2. OAuth Tokens API

Before using these endpoints you must create a public app, have a user install it, and capture the authorization `code` returned to your redirect URL.

### 2.1 Generate Initial Access and Refresh Tokens
- **Endpoint**: `POST /oauth/v1/token`
- **Headers**: `Content-Type: application/x-www-form-urlencoded`
- **Payload**:
  | Field | Type | Description |
  | --- | --- | --- |
  | `grant_type` | String | Must be `authorization_code`. |
  | `code` | String | The authorization code appended to your redirect URL during install. |
  | `redirect_uri` | String | Redirect URL configured for the app. |
  | `client_id` | String | App client ID. |
  | `client_secret` | String | App client secret. |
- **Example request**:
  ```bash
  curl --request POST \
    --url https://api.hubapi.com/oauth/v1/token \
    --header 'content-type: application/x-www-form-urlencoded' \
    --data 'grant_type=authorization_code&code=bcf33c57-dd7a-c7eb-4179-9241-e01bd&redirect_uri=https://www.domain.com/redirect&client_id=7933b042-0952-4e7d-a327dab-3dc&client_secret=7a572d8a-69bf-44c6-9a34-416aad3ad5'
  ```
- **Example response**:
  ```json
  {
    "token_type": "bearer",
    "refresh_token": "1e8fbfb1-8e96-4826-8b8d-c8af73715",
    "access_token": "CIrToaiiMhIHAAEAQAAAARiO1ooBIOP0sgEokuLtAEaOaTFnToZ3VjUbtl46MAAAAEAAAAAgAAAAAAAAAAAACAAAAAAAOABAAAAAAAAAAAAAAAQAkIUVrptEzQ4hQHP89Eoahkq-p7dVIAWgBgAA",
    "expires_in": 1800
  }
  ```

### 2.2 Refresh an Access Token
- **Endpoint**: `POST /oauth/v1/token`
- **Headers**: `Content-Type: application/x-www-form-urlencoded`
- **Payload**:
  | Field | Type | Description |
  | --- | --- | --- |
  | `grant_type` | String | Must be `refresh_token`. |
  | `refresh_token` | String | Previously issued refresh token. |
  | `client_id` | String | App client ID. |
  | `client_secret` | String | App client secret. |
- **Example request**:
  ```bash
  curl --request POST \
    --url https://api.hubapi.com/oauth/v1/token \
    --header 'content-type: application/x-www-form-urlencoded' \
    --data 'grant_type=refresh_token&refresh_token=1e8fbfb1-8e96-4826-8b8d-c8af73715&client_id=7933b042-0952-4e7d-a327dab-3dc&client_secret=7a572d8a-69bf-44c6-9a34-416aad3ad5'
  ```

### 2.3 Retrieve Access Token Metadata
- **Endpoint**: `GET /oauth/v1/access-tokens/{token}`
- **Headers**: Not specified beyond normal OAuth authentication.
- **Description**: Returns user, hub, scope, and expiration data for the supplied token.
- **Example response**:
  ```json
  {
    "token": "CNaKSIHAAEAQAAAARiO1ooBIOP0sgEokuLtATIU5m7Kzmjj0ihJJuKFq1TcIiHCqwE6MAAAAEEAAAAAAAAAAgAIUfmerBenQwc07ZHXy6atYNNW8XCVKA25hMVIAWgBgAA",
    "user": "user@domain.com",
    "hub_domain": "meowmix.com",
    "scopes": [
      "oauth",
      "crm.objects.contacts.read",
      "crm.objects.contacts.write"
    ],
    "signed_access_token": {
      "expiresAt": 1727190403926,
      "scopes": "AAEAAAAQ==",
      "hubId": 1234567,
      "userId": 293199,
      "appId": 111111,
      "signature": "5m7ihJJuKFq1TcIiHCqwE=",
      "scopeToScopeGroupPks": "AAAAQAAAAAAAAAACAAAAAAAAAAAAAIAAAAAAA4AEAAAAAAAAAAAAAABAC",
      "newSignature": "fme07ZHXy6atYNNW8XCU=",
      "hublet": "na1",
      "trialScopes": "",
      "trialScopeToScopeGroupPks": "",
      "isUserLevel": false
    },
    "hub_id": 1234567,
    "app_id": 111111,
    "expires_in": 1754,
    "user_id": 293199,
    "token_type": "access"
  }
  ```

### 2.4 Delete a Refresh Token
- **Endpoint**: `DELETE /oauth/v1/refresh-tokens/{token}`
- **Headers**: Not specified.
- **Description**: Removes only the refresh token when a user uninstalls the app. Access tokens created from that refresh token remain valid until they expire. The request does not uninstall the app or stop syncing data.
## 3. CMS API | Blog Posts

Last modified: September 4, 2025. Blog posts can be managed as drafts and published content. The API supports multi-language management and filtering.

### 3.1 Retrieve Blog Posts
- **Endpoints**:
  - `GET /cms/v3/blogs/posts/{postId}` to fetch a specific post.
  - `GET /cms/v3/blogs/posts` to list posts.
- **Headers**: Not specified.
- **Filters** (pass as query parameters using `property__operator=value`):
  - Operators: `eq`, `ne`, `contains`, `lt`, `lte`, `gt`, `gte`, `is_null`, `not_null`, `like`, `not_like`, `icontains`, `startswith`, `in`, `nin`.
  - Filterable properties and supported operators:
    | Property | Operators |
    | --- | --- |
    | `id` | `eq`, `in` |
    | `slug` | `eq`, `in`, `nin`, `icontains` |
    | `campaign` | `eq`, `in` |
    | `state` | `eq`, `ne`, `in`, `nin`, `contains` |
    | `publishDate` | `eq`, `gt`, `gte`, `lt`, `lte` |
    | `createdAt` / `updatedAt` | `eq`, `gt`, `gte`, `lt`, `lte` |
    | `name` | `eq`, `in`, `icontains` |
    | `archivedAt` | `eq`, `gt`, `gte`, `lt`, `lte` |
    | `createdById` / `updatedById` | `eq` |
    | `blogAuthorId` | `eq`, `in` |
    | `translatedFromId` | `is_null`, `not_null` |
    | `contentGroupId` | `eq`, `in` |
    | `tagId` | `eq`, `in` |
- **Publish state filters**:
  - `state=DRAFT`, `state=SCHEDULED`, or `state=PUBLISHED`.
- **Multi-language filters**:
  | Description | Query parameter |
  | --- | --- |
  | Primary post | `translatedFromId__is_null` |
  | Variation | `translatedFromId__not_null` |
  | Specific language group | `contentGroupId__eq=<groupId>` |
- **Sorting/Pagination**: `sort=<property>` (prefix with `-` for descending), `limit`, `offset`, and `after` cursor.
- **Example list request from the source**:
  ```bash
  curl \
    https://api.hubapi.com/cms/v3/blogs/posts?sort=-updatedAt&&language__not_null&limit=10&offset=10 \
    --request POST \
    --header "Content-Type: application/json"
  ```

### 3.2 Create a Blog Post
- **Endpoint**: `POST /cms/v3/blogs/posts`
- **Headers**: Not specified.
- **Payload**:
  ```json
  {
    "name": "Example blog post",
    "contentGroupId": "184993428780",
    "slug": "slug-at-the-end-of-the-url",
    "blogAuthorId": "4183274253",
    "metaDescription": "My meta description.",
    "useFeaturedImage": false,
    "postBody": "<p>Welcome to my blog post! Neat, huh?</p>"
  }
  ```
- **Field notes**:
  | Field | Type | Description |
  | --- | --- | --- |
  | `name` | String | Title of the post. |
  | `contentGroupId` | String | Parent blog ID (use the blog details API to fetch IDs). |
  | `slug` | String | URL slug. Defaults to a temporary slug derived from `name` if omitted; must be set before publishing. |
  | `blogAuthorId` | String | Author ID (use the blog authors API). |
  | `metaDescription` | String | Meta description. |
  | `useFeaturedImage` | Boolean | Defaults to `true`. Set to `false` to omit `featuredImage`. |
  | `postBody` | String | HTML body content. |

### 3.3 Update a Draft
- **Endpoint**: `PATCH /cms/v3/blogs/posts/{postId}/draft`
- **Headers**: Not specified.
- **Payload**: Provide the full blog post model for any nested objects being updated; partial updates of nested structures are not supported. Example:
  ```json
  {
    "name": "Example blog post",
    "slug": "my-updated-post"
  }
  ```
  A separate publish call is required to push the draft live.

### 3.4 Update and Publish Simultaneously
- **Endpoint**: `PATCH /cms/v3/blogs/posts/{postId}`
- **Headers**: Not specified.
- **Payload**: Same structure as the draft update but applies to both draft and live versions.
- **Publishing requirements when moving from draft to live** (fields must be present and valid): `name`, `contentGroupId`, `slug`, `blogAuthorId`, `metaDescription`, `featuredImage` (or `useFeaturedImage=false`), and `state` set to `PUBLISHED`.

### 3.5 Push a Draft Live
- **Endpoint**: `POST /cms/v3/blogs/posts/{postId}/draft/push-live`
- **Headers**: Not specified.
- **Payload**: Not required.

### 3.6 Schedule a Publish
- **Endpoint**: `POST /cms/v3/blogs/posts/schedule`
- **Headers**: Not specified.
- **Payload**: JSON containing `id` of the blog post and `publishDate` (ISO 8601).

### 3.7 Reset a Draft to Match Live Content
- **Endpoint**: `POST /cms/v3/blogs/posts/{postId}/draft/reset`
- **Headers**: Not specified.
- **Payload**: Not required.

### 3.8 Multi-language Management
- **Create a new language variant**: `POST /multi-language/create-language-variant`
  - Payload must include the `id` of the source blog post and the `language` identifier for the new variant.
- **Attach to an existing language group**: `POST /multi-language/attach-to-lang-group`
  - Payload includes the target post `id`, the variant `language`, and the `primaryId` of the primary post within the target group.
- **Detach from a language group**: `POST /multi-language/detach-from-lang-group`
  - Payload must contain the `id` of the blog post to detach.
## 4. Conversations Inbox & Messages API (Beta)

Last modified: September 4, 2025. All GET requests (and POST batch reads to the get actors endpoint) require the `conversations.read` scope. All other endpoints require `conversations.write`.

### 4.1 Filtering and Sorting Parameters
Common query parameters for inboxes, channels, channel accounts, threads, and messages:
- `sort`: Sort order; multiple properties supported.
- `after`: Cursor for paginated reads (use the value returned in `paging.next.after`).
- `limit`: Page size.

### 4.2 Inboxes
- **List inboxes**: `GET /conversations/v3/conversations/inboxes`
- **Get specific inbox**: `GET /conversations/v3/conversations/inboxes/{inboxId}`
- Headers/Payload: Not specified beyond authentication.

### 4.3 Channels and Channel Accounts
- **List channels**: `GET /conversations/v3/conversations/channels`
- **Get channel**: `GET /conversations/v3/conversations/channels/{channelId}`
- **List channel accounts**: `GET /conversations/v3/conversations/channel-accounts`
  - Optional query parameters: `channelId`, `inboxId`.
- **Get channel account**: `GET /conversations/v3/conversations/channel-accounts/{channelAccountId}`
- Example response structure:
  ```json
  {
    "total": 1,
    "results": [
      {
        "id": "148662",
        "channelId": "1000",
        "name": "New chatflow",
        "inboxId": "481939",
        "active": false,
        "authorized": true,
        "createdAt": "2019-10-04T15:24:39.136Z",
        "archived": false
      }
    ]
  }
  ```

### 4.4 Threads
- **List threads**: `GET /conversations/v3/conversations/threads`
  - Query parameters:
    | Parameter | Type | Description |
    | --- | --- | --- |
    | `inboxId` | Integer | Filter by inbox (single value only). |
    | `archived` | Boolean | Set `true` to fetch archived threads. |
    | `sort` | String | `id` (default) or `latestMessageTimestamp`. Sorting by `latestMessageTimestamp` also requires `latestMessageTimestampAfter`. |
    | `after` | String | Paging cursor (use with `sort=id`). |
    | `latestMessageTimestampAfter` | String | Minimum timestamp (only when sorting by `latestMessageTimestamp`). |
    | `limit` | Integer | Max 500. |
  - To fetch open or closed threads for a contact include `associatedContactId=<contactId>` and `threadStatus=OPEN` or `CLOSED`.
- **Get thread by ID**: `GET /conversations/v3/conversations/threads/{threadId}`

### 4.5 Messages
- **Get all messages in a thread**: `GET /conversations/v3/conversations/threads/{threadId}/messages`
- **Get a specific message**: `GET /conversations/v3/conversations/threads/{threadId}/messages/{messageId}`
- **Get original content for truncated messages**: `GET /conversations/v3/conversations/threads/{threadId}/messages/{messageId}/original-content`
- Messages include a `truncationStatus` of `NOT_TRUNCATED`, `TRUNCATED_TO_MOST_RECENT_REPLY`, or `TRUNCATED` for email threads.

### 4.6 Actors
- **Get actor**: `GET /conversations/v3/conversations/actors/{actorId}`
- Actor ID prefixes:
  | Prefix | Description |
  | --- | --- |
  | `A-` | HubSpot user (agent). |
  | `E-` | Email actor when HubSpot does not resolve it to a contact. |
  | `I-` | Integration (app) actor. |
  | `L-` | Customer agent actor. |
  | `S-` | System actor. |
  | `V-` | Visitor actor (contact ID). |

### 4.7 Update or Restore Threads
- **Update status**: `PATCH /conversations/v3/conversations/threads/{threadId}`
  - Payload: `{ "status": "OPEN" | "CLOSED" }`
- **Restore archived thread**: `PATCH /conversations/v3/conversations/threads/{threadId}?archived=true`
  - Payload: `{ "archived": false }`
- Note: Only status changes and restores are supported via this endpoint.

### 4.8 Archive Threads
- **Endpoint**: `DELETE /conversations/v3/conversations/threads/{threadId}`
- Description: Moves the thread to trash (permanently deleted after 30 days unless restored earlier).

### 4.9 Add Comments to Threads
- **Endpoint**: `POST /conversations/v3/conversations/threads/{threadId}/messages`
- **Payload fields for comments**:
  | Field | Description |
  | --- | --- |
  | `type` | Use `COMMENT` (or `MESSAGE`). |
  | `text` | Plain text content. |
  | `richText` | Optional HTML. |
  | `attachments` | Optional list of objects each containing a `fileId` hosted via the Files API. |
- **Example**:
  ```json
  {
    "type": "COMMENT",
    "text": "Can you follow up?",
    "richText": "<p>Can you follow up?</p>"
  }
  ```

### 4.10 Send Messages on Threads
- **Endpoint**: `POST /conversations/v3/conversations/threads/{threadId}/messages`
- **Payload fields for outbound messages**:
  | Field | Description |
  | --- | --- |
  | `type` | `MESSAGE` or `COMMENT`. |
  | `text` | Plain text content. |
  | `richText` | Optional HTML. |
  | `recipients` | For email, include `actorId`, `name`, `recipientField` (`TO`,`CC`,`BCC`), and `deliveryIdentifiers` (e.g., `{ "type": "HS_EMAIL_ADDRESS", "value": "user@example.com" }`). |
  | `senderActorId` | Agent actor ID sending the message. |
  | `channelId` | Channel type (e.g., `1000` chat, `1001` Facebook Messenger, `1002` email). |
  | `channelAccountId` | Channel account ID (copy from the latest message when replying). |
  | `subject` | Email subject (ignored for non-email channels). |
  | `attachments` | Either `{ "fileId": "https://..." }` for hosted files or quick reply definitions. |
- **Attachment formats**:
  - File attachment example:
    ```json
    {
      "fileId": "https://12345678.fs1.hubspotusercontent-na1.net/hubfs/12345678/doggo_video.mp4"
    }
    ```
  - Quick replies for Facebook Messenger or LiveChat:
    ```json
    {
      "type": "QUICK_REPLIES",
      "quickReplies": [
        { "label": "Yes", "value": "Yes", "valueType": "URL" },
        { "label": "No", "value": "No", "valueType": "TEXT" }
      ]
    }
    ```

### 4.11 Conversations Webhooks
Conversations webhooks require the `conversations.read` scope. Supported events:
- `conversation.creation`: new thread created.
- `conversation.deletion`: thread archived.
- `conversation.privacyDeletion`: thread permanently deleted.
- `conversation.propertyChange`: thread property changed (`assignedTo`, `status`, `isArchived`).
- `conversation.newMessage`: new message posted on a thread (`messageId`, `messageType`).

Webhook payloads always include `objectId`, the ID of the conversation thread.
## 5. CRM APIs and Commerce Payments

HubSpot CRM data is organized by object types identified by `objectTypeId` values (e.g., `0-1` contacts, `0-2` companies, `0-3` deals, `0-5` tickets, `0-8` line items, `0-14` quotes, `0-47` meetings, `0-53` invoices, `0-69` subscriptions, `0-101` payments, `0-115` users, `0-136` leads, `0-162` services, `0-420` listings, `2-XXX` custom objects). Use these IDs when calling CRM endpoints.

### 5.1 Generic CRM Object Endpoints
- **Create records**: `POST /crm/v3/objects/{objectTypeId}` (example: contacts use `0-1`; courses use `0-410`).
- **Retrieve records**: `GET /crm/v3/objects/{objectTypeId}`.
- **Update specific records**: e.g., `PATCH /crm/v3/objects/0-1/{contactId}` or `PATCH /crm/v3/objects/0-1/{contactEmail}?idProperty=email`.
- **Define properties**: `POST /crm/v3/properties/{objectTypeId}`.
- **Discover custom object type IDs**: `GET /crm/v3/schemas`.
- **Search objects/activities**: e.g., `POST /crm/v3/objects/0-48/search` for calls.
- Unique identifiers can use `hs_object_id` or any custom unique property supported by the endpoint via the `idProperty` parameter.

### 5.2 Commerce Payments API
_Last modified: September 26, 2025._ These endpoints require that the HubSpot account is configured for HubSpot payments or Stripe payment processing. Payments created directly through Commerce Hub cannot be modified or deleted via this API.

#### 5.2.1 Create Payments
- **Endpoint**: `POST /crm/v3/objects/commerce_payments`
- **Payload requirements**: include `properties.hs_initial_amount` and `properties.hs_initiated_date` at minimum. Optional `associations` can link the payment to other CRM objects at creation.
- **Example payload**:
  ```json
  {
    "properties": {
      "hs_initial_amount": "99.99",
      "hs_initiated_date": "2024-03-27T18:04:11.823Z",
      "hs_customer_email": "customer@example.com"
    },
    "associations": [
      {
        "to": { "id": 70791348501 },
        "types": [
          {
            "associationCategory": "HUBSPOT_DEFINED",
            "associationTypeId": 387
          }
        ]
      },
      {
        "to": { "id": 44446244097 },
        "types": [
          {
            "associationCategory": "HUBSPOT_DEFINED",
            "associationTypeId": 542
          }
        ]
      }
    ]
  }
  ```
- **Response**: includes HubSpot-generated properties such as `hs_payment_id`, timestamps, and association metadata (see source example for full field list).

#### 5.2.2 Retrieve Payments
- **List all**: `GET /crm/v3/objects/commerce_payments`
- **Get by ID**: `GET /crm/v3/objects/commerce_payments/{paymentId}`
- **Filter via search**: `POST /crm/v3/objects/commerce_payments/search`
  - Example request body to find refunded payments:
    ```json
    {
      "filterGroups": [
        {
          "filters": [
            {
              "propertyName": "hs_latest_status",
              "value": "refunded",
              "operator": "EQ"
            }
          ]
        }
      ],
      "properties": [
        "hs_latest_status",
        "hs_customer_email"
      ]
    }
    ```
- **Return specific properties**: include `?properties=<comma-separated list>` in GET requests.

#### 5.2.3 Update Payments
- **Endpoint**: `PATCH /crm/v3/objects/commerce_payments/{paymentId}`
- **Payload**: `{ "properties": { "hs_latest_status": "succeeded" } }`
- **Response**: contains default properties plus updated values.

#### 5.2.4 Delete Payments
- **Endpoint**: `DELETE /crm/v3/objects/commerce_payments/{paymentId}`
- **Behavior**: moves the payment to the recycling bin (permanent deletion after 90 days).

#### 5.2.5 Payment Properties
- **List all properties**: `GET /crm/v3/properties/commerce_payments`
- **Writable fields** (selection shown exactly as documented):
  - `hs_currency_code`, `hs_customer_email`, `hs_fees_amount`, `hs_initial_amount`, `hs_initiated_date`, `hs_internal_comment`, `hs_latest_status` (`processing`, `succeeded`, `failed`, `partially_refunded`, `refunded`, `processing_refund`, `disputed_won`, `disputed_lost`, `disputed_action_required`, `disputed_awaiting_decision`), `hs_payment_method_bank_or_issuer`, `hs_payment_method_last_4`, `hs_payment_method_type` (`card`, `ach`, `cash`, `check`, `wire_transfer`, `other`, `sepa`, `bacs`, `pads`), `hs_payout_date`, `hs_processor_type` (`hs_payments`, `byo_stripe`, `none`, `quickbooks`, `xero`), `hs_reference_number`, `hs_refunds_amount`, billing address fields, shipping address fields, `hs_line_item_discounts_amount`, `hs_shipping_ship_to_name`.
- **Read-only fields**: `hs_digital_wallet_type` (`apple_pay`, `google_pay`, `amex_express_checkout`, `link`, `masterpass`, `samsung_pay`, `visa_checkout`), settlement currency variants of fees/amounts, `hs_max_refundable_amount_in_portal_currency`, `hs_order_discount_code`, `hs_order_discount_amount`, `hs_order_discount_percentage`, `hs_payment_id`, `hs_payment_method`, `hs_payment_source_app` (`SALES_CHECKOUT`, `QUOTE`, `INVOICE`, `MIGRATION`, `SUBSCRIPTION`), `hs_payment_source_id`, `hs_payment_source_name`, `hs_payment_source_url`, `hs_payment_type`, `hs_platform_fee` variations, `hs_refunds_amount_in_portal_currency`, `hs_settlement_currency_code`, `hs_total_discounts_amount`.

#### 5.2.6 Associations
- Payments can associate with: Companies (`389`), Contacts (`387`), Deals (`391`), Discounts (`428`), Feedback submissions (`1170`), Invoices (`542`), Line items (`395`), Orders (`524`), Payment links (`476`), Quotes (`397`), Subscriptions (`393`).
- **Retrieve association type labels**: `GET /crm/v4/associations/commerce_payments/{toObjectType}/labels`
- **Update association**: `PUT /crm/v3/objects/commerce_payments/{paymentId}/associations/{toObjectType}/{toObjectId}/{associationTypeId}`
  - Example to associate an order: `/crm/v3/objects/commerce_payments/{paymentId}/associations/order/{orderId}/523`
- **Remove association**: `DELETE /crm/v3/objects/commerce_payments/{paymentId}/associations/{toObjectType}/{toObjectId}/{associationTypeId}`
- **Retrieve associated contact IDs**: `GET /crm/v3/objects/commerce_payments/{contactId}/associations/contact`
  - Example response:
    ```json
    {
      "results": [
        {
          "id": "301",
          "type": "commerce_payment_to_contact"
        }
      ]
    }
    ```
  - Use returned IDs with other CRM APIs, e.g., `GET /crm/v3/objects/contacts/{contactId}`.

## 6. Webhooks v4 Journal and Management APIs (Beta)

Last modified: August 22, 2025. These APIs use OAuth 2.0 with a client credentials token representing your app. Include `Authorization: Bearer <token>` in requests.

### 6.1 Required Scopes
Authorize the following scopes based on usage:
- `developer.webhooks_journal.read`
- `developer.webhooks_journal.subscriptions.read`
- `developer.webhooks_journal.subscriptions.write`
- `developer.webhooks_journal.snapshots.read`
- `developer.webhooks_journal.snapshots.write`
Also include object-specific scopes (e.g., `crm.contacts.read`) for the data you subscribe to.

### 6.2 Journal Retrieval Endpoints
- **Get earliest entry**: `GET /webhooks/v4/journal/earliest`
- **Get latest entry**: `GET /webhooks/v4/journal/latest`
- **Get next entry after an offset**: `GET /webhooks/v4/journal/offset/{offset}/next`
- **Response format** (all three endpoints return the same structure):
  ```json
  {
    "url": "https://s3.amazonaws.com/bucket/path/to/journal/file.json",
    "expiresAt": "2024-01-01T12:00:00Z",
    "currentOffset": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```
Download the file at `url` before it expires to process events. Store `currentOffset` for pagination.

### 6.3 Subscriptions API
- **Create or update subscriptions**: `POST /webhooks/v4/subscriptions`
  - Payload fields (fields marked * are required):
    | Field | Type | Description |
    | --- | --- | --- |
    | `objectTypeId`* | String | Object type identifier (e.g., `0-1`). |
    | `subscriptionType`* | String | `OBJECT` or `ASSOCIATION`. |
    | `portalId`* | Number | HubSpot account ID. |
    | `actions`* | Array | `CREATE`, `UPDATE`, `DELETE`, `MERGE`, `RESTORE`, `ASSOCIATION_ADDED`, `ASSOCIATION_REMOVED`, `SNAPSHOT`. |
    | `properties` | Array | Object properties to include in events. |
    | `objectIds` | Array | Specific object IDs to monitor. |
    | `associatedObjectTypeIds` | Array | Object types relevant to association events. |
  - Example payload (OBJECT subscription):
    ```json
    {
      "objectTypeId": "0-1",
      "subscriptionType": "OBJECT",
      "portalId": 12345,
      "actions": ["CREATE", "UPDATE", "DELETE"],
      "properties": ["email", "firstname", "lastname"],
      "objectIds": [1001, 1002, 1003]
    }
    ```
- **Subscribe to app lifecycle events**: `POST /webhooks/v4/subscriptions`
  - Payload:
    ```json
    {
      "subscriptionType": "APP_LIFECYCLE_EVENT",
      "eventTypeId": "4-1909196",
      "properties": ["string"]
    }
    ```
  - `eventTypeId` options: `4-1909196` (install), `4-1916193` (uninstall).
- **List subscriptions**: `GET /webhooks/v4/subscriptions`
- **Delete a subscription**: `DELETE /webhooks/v4/subscriptions/{subscriptionId}`
- **Delete all subscriptions for a portal**: `DELETE /webhooks/v4/subscriptions/portals/{portalId}`
- Responses for create/list show metadata like `id`, `appId`, `actions`, timestamps, and deletion status.

### 6.4 Snapshots API
- **Create CRM object snapshots**: `POST /webhooks/v4/snapshots/crm`
  - Payload fields:
    | Field | Type | Description |
    | --- | --- | --- |
    | `snapshotRequests` | Array | Each entry includes `portalId`, `objectId`, `objectTypeId`, and `properties` (array of property names to capture). |
  - Example:
    ```json
    {
      "snapshotRequests": [
        {
          "portalId": 12345,
          "objectId": 1001,
          "objectTypeId": "0-1",
          "properties": ["email", "firstname", "lastname", "phone"]
        },
        {
          "portalId": 12345,
          "objectId": 1002,
          "objectTypeId": "0-1",
          "properties": ["email", "company"]
        }
      ]
    }
    ```

### 6.5 Event Payload Examples
- Contact creation/update, association added, and app lifecycle journal event samples are as documented (see source for exact JSON). They include fields such as `offset`, `journalEvents`, `type`, `portalId`, `occurredAt`, `action`, `objectTypeId`, `objectId`, `propertyChanges`, and `publishedAt`.

### 6.6 Error Handling and Rate Limits
- **Success codes**: `200 OK`, `204 No Content`.
- **Error codes**: `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `429 Too Many Requests`, `500 Internal Server Error`.
- **Error response format**:
  ```json
  {
    "status": "error",
    "message": "Invalid subscription type provided",
    "correlationId": "550e8400-e29b-41d4-a716-446655440000",
    "category": "VALIDATION_ERROR"
  }
  ```
- **Rate limits**:
  - Journal API: 100 requests/sec/app
  - Subscriptions API: 50 requests/sec/app
  - Snapshots API: 10 requests/sec/app
  - `429` responses include `Retry-After` headers.

### 6.7 Best Practices (from source text)
- **Journal processing**: Process files chronologically, store offsets, download before URLs expire, use exponential backoff on errors.
- **Subscription management**: Filter precisely, request only needed properties, batch changes, tidy unused subscriptions.
- **Snapshot usage**: Batch requests, request only necessary properties, ensure records exist, remember snapshots capture state at request time.
- **Error handling**: Implement retries with backoff, log correlation IDs, validate requests before sending, monitor usage/error rates.
## 7. Marketing | Transactional Email APIs

Transactional email options include in-app configuration, SMTP API, and the Single-Send API. Any domains used in the `From` address must be connected as email sending domains in HubSpot.

### 7.1 SMTP API Tokens
- **Create token**: `POST /marketing/v3/transactional/smtp-tokens/`
  - **Payload**: JSON containing `createContact` (boolean) and `campaignName` (string).
  - **Response fields**: `id` (SMTP username), `createdBy`, `password` (only returned at creation), `emailCampaignId`, `createdAt`, `createContact`, `campaignName`.
- **Token monitoring**: HubSpot automatically deactivates tokens exposed publicly (e.g., on GitHub) and notifies you. Tokens created via the public API expire after 12 months.
- **List by campaign or campaign ID**: `GET /marketing/v3/transactional/smtp-tokens`
  - Include either `campaignName` or `emailCampaignId` query parameter.
  - Response includes `results` (collection of `SmtpApiTokenView`) and `paging.next.after`.
- **Get token by ID**: `GET /marketing/v3/transactional/smtp-tokens/{tokenId}`
- **Reset password**: `POST /marketing/v3/transactional/smtp-tokens/{tokenId}/password-reset`
  - Response returns the same fields as token retrieval (including the new password at reset time).
- **Delete token**: `DELETE /marketing/v3/transactional/smtp-tokens/{tokenId}`
- **SMTP login settings**:
  | Setting | Value |
  | --- | --- |
  | Hostname | `smtp.hubapi.com` (global) or `smtp-eu1.hubapi.com` (EU) |
  | Ports | `25` or `587` for STARTTLS, `465` for direct TLS |
  | Username | Token `id` |
  | Password | Token `password` |

### 7.2 Single-Send API
Templates must be created and (optionally) published inside HubSpot. The template `emailId` appears in the URL when editing (draft) or on the email details page (published).

#### 7.2.1 Send an Email
- **Endpoint**: `POST /marketing/v3/transactional/single-email/send`
- **Payload structure**:
  | Field | Description |
  | --- | --- |
  | `emailId` | Numeric content ID of the transactional email. |
  | `message` | JSON object; `to` is required. Optional fields: `from`, `sendId` (prevents duplicate sends), `replyTo` (list), `cc` (list), `bcc` (list). |
  | `contactProperties` | JSON map of contact property updates to apply while sending (e.g., `{ "last_paid_date": "2022-03-01" }`). |
  | `customProperties` | JSON map of template tokens referenced via `{{ custom.PROPERTY_NAME }}`; supports arrays for programmable email content. |
- **Example request with contact properties**:
  ```json
  {
    "emailId": 4126643121,
    "message": {
      "to": "jdoe@hubspot.com",
      "sendId": "6"
    },
    "contactProperties": {
      "last_paid_date": "2022-03-01",
      "firstname": "jane"
    }
  }
  ```
- **Example request with custom properties**:
  ```json
  {
    "emailId": 4126643121,
    "message": {
      "to": "jdoe@hubspot.com",
      "sendId": "6"
    },
    "customProperties": {
      "purchaseUrl": "https://example.com/link-to-product",
      "productName": "vanilla"
    }
  }
  ```
- **Example using array-based custom properties**:
  ```json
  {
    "emailId": 4126643122,
    "message": {
      "to": "jdoe@hubspot.com",
      "sendId": "7"
    },
    "customProperties": {
      "exampleArray": [
        { "firstKey": "someValue", "secondKey": "anotherValue" },
        { "firstKey": "value1", "secondKey": "value2" }
      ]
    }
  }
  ```
  In templates you can iterate over `custom.exampleArray` using HubL.

#### 7.2.2 Send Response
The send endpoint responds with:
- `requestedAt`: Timestamp when the send was requested.
- `statusId`: Identifier used to poll send status.
- `status`: `PENDING`, `PROCESSING`, `CANCELED`, or `COMPLETE`.

#### 7.2.3 Query Send Status
- **Endpoint**: `GET https://api.hubapi.com/marketing/v3/email/send-statuses/{statusId}`
- **Response fields**: `sendResult`, `requestedAt`, `startedAt`, `completedAt`, `statusId`, `status`, `eventId`.
- **`sendResult` values**:
  - `SENT`
  - `QUEUED`
  - `PORTAL_SUSPENDED`
  - `INVALID_TO_ADDRESS`
  - `BLOCKED_DOMAIN`
  - `PREVIOUSLY_BOUNCED`
  - `PREVIOUS_SPAM`
  - `INVALID_FROM_ADDRESS`
  - `MISSING_CONTENT`
  - `MISSING_TEMPLATE_PROPERTIES`
## 8. Feature Flags API for App Cards

Use the Feature Flags API (root path `https://api.hubapi.com/feature-flags/v3/{appId}`) to control access to legacy CRM cards and new app cards during migration to UI extensions. The API currently supports the `hs-release-app-cards` and `hs-hide-crm-cards` flags. All requests in this section use a developer API key via the `hapikey` query parameter as shown in the source examples.

### 8.1 Set a Single Test Account Flag State
- **Endpoint**: `PUT /feature-flags/v3/{appId}/flags/hs-release-app-cards/portals/{portalId}?hapikey={developerApiKey}`
- **Payload**:
  ```json
  { "flagState": "ON" }
  ```
- Purpose: enable app cards inside a developer test account before impacting production installs.

### 8.2 Batch Set Portal Flag States (hs-release-app-cards)
- **Endpoint**: `POST /feature-flags/v3/{appId}/flags/hs-release-app-cards/portals/batch/upsert?hapikey={developerApiKey}`
- **Payload**:
  ```json
  {
    "portalStates": [
      { "portalId": 1234, "flagState": "OFF" },
      { "portalId": 4567, "flagState": "OFF" },
      { "portalId": 78910, "flagState": "OFF" }
    ]
  }
  ```
- Use cases: temporarily disable new cards for all existing installs, or selectively enable subsets by setting `flagState` to `ON` for chosen accounts.

### 8.3 Set Default Flag State (hs-release-app-cards)
- **Endpoint**: `PUT /feature-flags/v3/{appId}/flags/hs-release-app-cards?hapikey={developerApiKey}`
- **Payload** (example):
  ```json
  { "defaultState": "ON" }
  ```
- Use case: after turning existing installs OFF, set the default to `ON` so future installs automatically see new cards.

### 8.4 Batch Delete Portal Flag States (hs-release-app-cards)
- **Endpoint**: `POST /feature-flags/v3/{appId}/flags/hs-release-app-cards/portals/batch/delete?hapikey={developerApiKey}`
- **Payload**:
  ```json
  { "portalIds": [1234, 4567, 78910] }
  ```
- Purpose: remove per-portal overrides once they no longer need special handling.

### 8.5 List Accounts with a Set Flag State
- **Endpoint (as documented)**: `GET /feature-flags/v3//flags/hs-release-app-cards/portals/`
- Returns the accounts that still have explicit flag states (e.g., still `OFF`).

### 8.6 Delete the App Flag
- **Endpoint**: `DELETE /feature-flags/v3/{appId}/flags/hs-release-app-cards?hapikey={developerApiKey}`
- Use when rollout is complete or when releasing app cards to all accounts simultaneously.

### 8.7 Manage Legacy CRM Card Visibility (hs-hide-crm-cards)
1. **Initialize flag**: `PUT /feature-flags/v3/{appId}/flags/hs-hide-crm-cards?hapikey={developerApiKey}` with payload `{ "defaultState": "OFF" }` so existing installs keep seeing legacy cards.
2. **Batch set install states**: `POST /feature-flags/v3/{appId}/flags/hs-hide-crm-cards/portals/batch/upsert?hapikey={developerApiKey}` with `flagState": "OFF"` for each existing portal.
3. **Prevent new installs from seeing legacy cards**: `PUT /feature-flags/v3/{appId}/flags/hs-hide-crm-cards?hapikey={developerApiKey}` with payload `{ "defaultState": "ON" }`.
4. **Remove portals after upgrade**: `POST /feature-flags/v3/{appId}/flags/hs-hide-crm-cards/portals/batch/delete?hapikey={developerApiKey}` with their IDs.
5. **Delete the flag once all installs have upgraded**: `DELETE /feature-flags/v3/{appId}/flags/hs-hide-crm-cards?hapikey={developerApiKey}`.

### 8.8 Feature Flag Reference Summary
- App flag endpoints (hs-release-app-cards): retrieve flags, retrieve accounts with set state, set flag, delete flag.
- Account flag state endpoints: delete a specific account flag state, retrieve account flag state, batch delete, batch set, set single account state. (The original documentation lists these operations without additional parameter details.)

