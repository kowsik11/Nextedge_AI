from __future__ import annotations

from typing import Any, Dict

SampleSpec = Dict[str, Any]


HUBSPOT_TEST_SAMPLES: Dict[str, SampleSpec] = {
  # 1. Automation API
  "1-1-complete-a-blocked-custom-action-execution-get-callbacks-callbackid-complete": {
    "path": "/callbacks/123/complete",
  },

  # 2. OAuth Tokens API
  "2-1-generate-initial-access-and-refresh-tokens-post-oauth-v1-token": {
    "payload_type": "form",
    "payload": {
      "grant_type": "authorization_code",
      "code": "sample_authorization_code",
      "redirect_uri": "https://example.com/oauth/callback",
      "client_id": "demo-client-id",
      "client_secret": "demo-client-secret",
    },
  },
  "2-2-refresh-an-access-token-post-oauth-v1-token": {
    "payload_type": "form",
    "payload": {
      "grant_type": "refresh_token",
      "refresh_token": "sample_refresh_token",
      "client_id": "demo-client-id",
      "client_secret": "demo-client-secret",
    },
  },
  "2-3-retrieve-access-token-metadata-get-oauth-v1-access-tokens-token": {
    "path": "/oauth/v1/access-tokens/sample-access-token",
  },
  "2-4-delete-a-refresh-token-delete-oauth-v1-refresh-tokens-token": {
    "path": "/oauth/v1/refresh-tokens/sample-refresh-token",
  },

  # 3. CMS Blog Posts
  "3-1-retrieve-blog-posts-get-cms-v3-blogs-posts-postid": {
    "path": "/cms/v3/blogs/posts/123456",
  },
  "3-1-retrieve-blog-posts-get-cms-v3-blogs-posts": {
    "path": "/cms/v3/blogs/posts",
    "query": {"limit": 5},
  },
  "3-2-create-a-blog-post-post-cms-v3-blogs-posts": {
    "payload": {
      "name": "Codex Sample Blog Post",
      "contentGroupId": "244205163",
      "slug": "codex-sample-post",
      "blogAuthorId": "258546201299",
      "metaDescription": "Synthetic payload triggered from the Tests page.",
      "useFeaturedImage": False,
      "postBody": "<p>This is a sample payload triggered from the Safe Point control panel.</p>",
    },
  },
  "3-3-update-a-draft-patch-cms-v3-blogs-posts-postid-draft": {
    "path": "/cms/v3/blogs/posts/123456/draft",
    "payload": {
      "name": "Updated Sample Draft",
      "postBody": "<p>Updated draft content.</p>",
    },
  },
  "3-4-update-and-publish-simultaneously-patch-cms-v3-blogs-posts-postid": {
    "path": "/cms/v3/blogs/posts/123456",
    "payload": {
      "name": "Updated Live Post",
      "postBody": "<p>Immediate publish update.</p>",
      "state": "PUBLISHED",
    },
  },
  "3-5-push-a-draft-live-post-cms-v3-blogs-posts-postid-draft-push-live": {
    "path": "/cms/v3/blogs/posts/123456/draft/push-live",
  },
  "3-6-schedule-a-publish-post-cms-v3-blogs-posts-schedule": {
    "payload": {"id": "123456", "publishDate": "2025-09-01T12:00:00Z"},
  },
  "3-7-reset-a-draft-to-match-live-content-post-cms-v3-blogs-posts-postid-draft-reset": {
    "path": "/cms/v3/blogs/posts/123456/draft/reset",
  },

  # 4. Conversations Inbox
  "4-8-archive-threads-delete-conversations-v3-conversations-threads-threadid": {
    "path": "/conversations/v3/conversations/threads/123456789",
  },
  "4-9-add-comments-to-threads-post-conversations-v3-conversations-threads-threadid-messages": {
    "path": "/conversations/v3/conversations/threads/123456789/messages",
    "payload": {
      "type": "COMMENT",
      "text": "Can you follow up on this conversation?",
      "richText": "<p>Can you follow up on this conversation?</p>",
    },
  },
  "4-10-send-messages-on-threads-post-conversations-v3-conversations-threads-threadid-messages": {
    "path": "/conversations/v3/conversations/threads/123456789/messages",
    "payload": {
      "type": "MESSAGE",
      "text": "Testing outbound message from Safe Point UI.",
      "richText": "<p>Testing outbound message from Safe Point UI.</p>",
      "recipients": [
        {
          "actorId": "E-sample@hubspot.com",
          "name": "Sample Recipient",
          "recipientField": "TO",
          "deliveryIdentifiers": [{"type": "HS_EMAIL_ADDRESS", "value": "sample@hubspot.com"}],
        }
      ],
      "senderActorId": "A-123456",
      "channelId": "1002",
      "channelAccountId": "654321",
      "subject": "Follow-up",
    },
  },

  # 5. Commerce payments
  "5-2-commerce-payments-api-post-crm-v3-objects-commerce-payments": {
    "payload": {
      "properties": {
        "hs_initial_amount": "99.99",
        "hs_initiated_date": "2024-03-27T18:04:11.823Z",
        "hs_customer_email": "customer@example.com",
      },
    },
  },
  "5-2-commerce-payments-api-patch-crm-v3-objects-commerce-payments-paymentid": {
    "path": "/crm/v3/objects/commerce_payments/123456789",
    "payload": {"properties": {"hs_latest_status": "succeeded"}},
  },
  "5-2-commerce-payments-api-delete-crm-v3-objects-commerce-payments-paymentid": {
    "path": "/crm/v3/objects/commerce_payments/123456789",
  },

  # 7. Transactional email
  "7-2-single-send-api-post-marketing-v3-transactional-single-email-send": {
    "payload": {
      "emailId": 4126643121,
      "message": {"to": "jdoe@example.com", "sendId": "sample-send-id"},
      "contactProperties": {
        "firstname": "Sample",
        "last_paid_date": "2024-03-01",
      },
      "customProperties": {
        "purchaseUrl": "https://example.com/purchase",
        "productName": "Sample Widget",
      },
    },
  },
  "7-2-single-send-api-get-https-api-hubapi-com-marketing-v3-email-send-statuses-statusid": {
    "path": "/marketing/v3/email/send-statuses/sample-status-id",
  },

  # 8. Feature flags
  "8-1-set-a-single-test-account-flag-state-put-feature-flags-v3-appid-flags-hs-release-app-cards-portals-portalid-hapikey-developerapikey": {
    "path": "/feature-flags/v3/123456/flags/hs-release-app-cards/portals/987654",
    "query": {"hapikey": "demo-key"},
    "payload": {"flagState": "ON"},
  },
  "8-2-batch-set-portal-flag-states-hs-release-app-cards-post-feature-flags-v3-appid-flags-hs-release-app-cards-portals-batch-upsert-hapikey-developerapikey": {
    "path": "/feature-flags/v3/123456/flags/hs-release-app-cards/portals/batch/upsert",
    "query": {"hapikey": "demo-key"},
    "payload": {
      "portalStates": [
        {"portalId": 1234, "flagState": "OFF"},
        {"portalId": 5678, "flagState": "OFF"},
      ]
    },
  },
  "8-3-set-default-flag-state-hs-release-app-cards-put-feature-flags-v3-appid-flags-hs-release-app-cards-hapikey-developerapikey": {
    "path": "/feature-flags/v3/123456/flags/hs-release-app-cards",
    "query": {"hapikey": "demo-key"},
    "payload": {"defaultState": "ON"},
  },
  "8-4-batch-delete-portal-flag-states-hs-release-app-cards-post-feature-flags-v3-appid-flags-hs-release-app-cards-portals-batch-delete-hapikey-developerapikey": {
    "path": "/feature-flags/v3/123456/flags/hs-release-app-cards/portals/batch/delete",
    "query": {"hapikey": "demo-key"},
    "payload": {"portalIds": [1234, 5678]},
  },
  "8-6-delete-the-app-flag-delete-feature-flags-v3-appid-flags-hs-release-app-cards-hapikey-developerapikey": {
    "path": "/feature-flags/v3/123456/flags/hs-release-app-cards",
    "query": {"hapikey": "demo-key"},
  },
}
