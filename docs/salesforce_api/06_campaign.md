# Salesforce REST API - Campaign Object

## Overview
The Campaign object represents a marketing initiative in Salesforce (email campaigns, events, webinars, etc.).

**HubSpot Equivalent:** *Marketing Events / Lists (no direct equivalent)*

---

## Authentication

**Required Headers:**
```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

---

## Base URL Pattern
```
https://{instance_url}/services/data/v65.0/sobjects/Campaign
```

---

## 1. CREATE Campaign

### Endpoint
```
POST /services/data/v65.0/sobjects/Campaign
```

### Request Body (JSON Payload)
```json
{
  "Name": "Q1 2025 Webinar Series",
  "Type": "Webinar",
  "Status": "Planned",
  "StartDate": "2025-02-01",
  "EndDate": "2025-03-31",
  "IsActive": true,
  "Description": "Series of 4 webinars covering product features and best practices",
  "BudgetedCost": 5000,
  "ExpectedRevenue": 50000,
  "ExpectedResponse": 200,
  "NumberSent": 1000,
  "ParentId": null
}
```

### Response (Success - 201 Created)
```json
{
  "id": "7011234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields
- **Name** (campaign name)

---

## 2. READ Campaign (Get by ID)

### Endpoint
```
GET /services/data/v65.0/sobjects/Campaign/{campaign_id}
```

### Response (Success - 200 OK)
```json
{
  "attributes": {
    "type": "Campaign",
    "url": "/services/data/v65.0/sobjects/Campaign/7011234567890ABC"
  },
  "Id": "7011234567890ABC",
  "Name": "Q1 2025 Webinar Series",
  "Type": "Webinar",
  "Status": "Planned",
  "StartDate": "2025-02-01",
  "EndDate": "2025-03-31",
  "IsActive": true,
  "Description": "Series of 4 webinars...",
  "BudgetedCost": 5000,
  "ExpectedRevenue": 50000,
  "ExpectedResponse": 200,
  "NumberSent": 1000,
  "NumberOfLeads": 45,
  "NumberOfConvertedLeads": 12,
  "NumberOfContacts": 78,
  "NumberOfOpportunities": 8,
  "AmountAllOpportunities": 125000,
  "AmountWonOpportunities": 0,
  "CreatedDate": "2025-01-15T10:30:00.000+0000"
}
```

---

## 3. SEARCH Campaign (SOQL Query)

### Get Active Campaigns
```
GET /services/data/v65.0/query?q=SELECT Id, Name, Type, Status, StartDate, EndDate FROM Campaign WHERE IsActive = true
```

### Get Campaigns by Type
```
SELECT Id, Name, Status, StartDate, EndDate, BudgetedCost 
FROM Campaign 
WHERE Type = 'Webinar' 
ORDER BY StartDate DESC
```

### Response
```json
{
  "totalSize": 3,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Campaign",
        "url": "/services/data/v65.0/sobjects/Campaign/7011234567890ABC"
      },
      "Id": "7011234567890ABC",
      "Name": "Q1 2025 Webinar Series",
      "Type": "Webinar",
      "Status": "Planned",
      "StartDate": "2025-02-01",
      "EndDate": "2025-03-31",
      "BudgetedCost": 5000
    }
  ]
}
```

---

## 4. UPDATE Campaign

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Campaign/{campaign_id}
```

### Request Body
```json
{
  "Status": "In Progress",
  "ActualCost": 4500,
  "NumberSent": 1250,
  "NumberOfResponses": 180
}
```

### Response (Success - 204 No Content)

---

## 5. DELETE Campaign

### Endpoint
```
DELETE /services/data/v65.0/sobjects/Campaign/{campaign_id}
```

### Response (Success - 204 No Content)

**Note:** Cannot delete campaigns with associated Campaign Members.

---

## 6. ADD Campaign Member

### Endpoint
```
POST /services/data/v65.0/sobjects/CampaignMember
```

### Request Body
```json
{
  "CampaignId": "7011234567890ABC",
  "ContactId": "0031234567890XYZ",
  "Status": "Sent"
}
```

**Or with Lead:**
```json
{
  "CampaignId": "7011234567890ABC",
  "LeadId": "00Q1234567890XYZ",
  "Status": "Sent"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "00v1234567890ABC",
  "success": true,
  "errors": []
}
```

---

## Python Example

```python
import requests

instance_url = "https://yourinstance.my.salesforce.com"
access_token = "YOUR_ACCESS_TOKEN"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Create Campaign
def create_campaign(name, type, start_date, end_date, budgeted_cost=0):
    url = f"{instance_url}/services/data/v65.0/sobjects/Campaign"
    
    payload = {
        "Name": name,
        "Type": type,
        "Status": "Planned",
        "StartDate": start_date,  # Format: YYYY-MM-DD
        "EndDate": end_date,
        "IsActive": True,
        "BudgetedCost": budgeted_cost
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Add Contact to Campaign
def add_contact_to_campaign(campaign_id, contact_id, status="Sent"):
    url = f"{instance_url}/services/data/v65.0/sobjects/CampaignMember"
    
    payload = {
        "CampaignId": campaign_id,
        "ContactId": contact_id,
        "Status": status
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Add Lead to Campaign
def add_lead_to_campaign(campaign_id, lead_id, status="Sent"):
    url = f"{instance_url}/services/data/v65.0/sobjects/CampaignMember"
    
    payload = {
        "CampaignId": campaign_id,
        "LeadId": lead_id,
        "Status": status
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Update Campaign Status
def update_campaign_status(campaign_id, new_status, actual_cost=None):
    url = f"{instance_url}/services/data/v65.0/sobjects/Campaign/{campaign_id}"
    
    updates = {"Status": new_status}
    if actual_cost is not None:
        updates["ActualCost"] = actual_cost
    
    response = requests.patch(url, json=updates, headers=headers)
    return response.status_code == 204

# Usage
campaign = create_campaign(
    name="Q1 2025 Webinar Series",
    type="Webinar",
    start_date="2025-02-01",
    end_date="2025-03-31",
    budgeted_cost=5000
)
campaign_id = campaign["id"]
print(f"Created Campaign ID: {campaign_id}")

# Add contacts/leads to campaign
add_contact_to_campaign(campaign_id, "0031234567890XYZ", "Sent")
add_lead_to_campaign(campaign_id, "00Q1234567890XYZ", "Sent")

# Update status
update_campaign_status(campaign_id, "In Progress", 4500)
```

---

## Common Field Reference

| Field API Name | Type | Description | Required |
|----------------|------|-------------|----------|
| Name | String(80) | Campaign name | Yes |
| Type | Picklist | Campaign type | No |
| Status | Picklist | Campaign status | No |
| StartDate | Date | Campaign start date | No |
| EndDate | Date | Campaign end date | No |
| IsActive | Boolean | Whether campaign is active | No |
| Description | Textarea | Campaign description | No |
| BudgetedCost | Currency | Budgeted cost | No |
| ActualCost | Currency | Actual cost spent | No |
| ExpectedRevenue | Currency | Expected revenue | No |
| ExpectedResponse | Number | Expected number of responses | No |
| NumberSent | Number | Number of people targeted | No |
| NumberOfLeads | Number | Number of associated leads | Read-Only |
| NumberOfContacts | Number | Number of associated contacts | Read-Only |
| NumberOfConvertedLeads | Number | Converted leads from campaign | Read-Only |
| NumberOfOpportunities | Number | Opportunities influenced | Read-Only |
| NumberOfResponses | Number | Number of responses | Read-Only |
| AmountAllOpportunities | Currency | Total opportunity amount | Read-Only |
| AmountWonOpportunities | Currency | Won opportunity amount | Read-Only |
| ParentId | Reference | Parent Campaign ID | No |
| OwnerId | Reference | Campaign owner (user) ID | No |

---

## Campaign Type Picklist Values

- **Email**
- **Webinar**
- **Conference**
- **Trade Show**
- **Public Relations**
- **Partners**
- **Referral Program**
- **Advertisement**
- **Banner Ads**
- **Direct Mail**
- **Telemarketing**
- **Other**

---

## Campaign Status Picklist Values

- **Planned**
- **In Progress**
- **Completed**
- **Aborted**

---

## Campaign Member Status Values

Standard statuses (customizable per campaign):
- **Sent**
- **Responded**
- **Attended** (for events)
- **Registered** (for events)

---

## cURL Examples

### Create Campaign
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Campaign" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "Q1 2025 Webinar Series",
    "Type": "Webinar",
    "Status": "Planned",
    "StartDate": "2025-02-01",
    "EndDate": "2025-03-31",
    "BudgetedCost": 5000
  }'
```

### Add Contact to Campaign
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/CampaignMember" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "CampaignId": "7011234567890ABC",
    "ContactId": "0031234567890XYZ",
    "Status": "Sent"
  }'
```

---

## Best Practices

1. **Set clear start/end dates** for tracking and reporting
2. **Track costs** - Set BudgetedCost and update ActualCost
3. **Add members systematically** - Use CampaignMember for tracking
4. **Update status regularly** - Keep campaign status current
5. **Use hierarchies** - Set ParentId for campaign programs
6. **Track ROI** - Monitor AmountWonOpportunities vs ActualCost
7. **Set expected metrics** - Use ExpectedRevenue and ExpectedResponse for planning
8. **Link opportunities** - Set Opportunity.CampaignId for attribution
9. **Use proper types** - Choose appropriate campaign type
10. **Activate campaigns** - Set IsActive = true for reporting

---

## Campaign Hierarchy

Use **ParentId** to create campaign hierarchies:
- Parent Campaign: "2025 Marketing Program"
  - Child Campaign: "Q1 Webinar Series"
  - Child Campaign: "Q2 Trade Show"
  - Child Campaign: "Q3 Email Campaign"

---

## Marketing Attribution

Track campaign influence on opportunities:
1. Add contacts/leads to campaign using CampaignMember
2. When creating Opportunity, set **Opportunity.CampaignId**
3. Salesforce automatically tracks **Primary Campaign Source**
4. Use Campaign Influence for multi-touch attribution

---

## Next Steps

- See [Lead API Documentation](./03_lead.md) to add leads to campaigns
- See [Contact API Documentation](./01_contact.md) to add contacts to campaigns
- See [Opportunity API Documentation](./04_opportunity.md) for campaign attribution
- Use Campaign Member object for detailed tracking
