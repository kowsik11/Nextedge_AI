# Salesforce REST API - Opportunity Object

## Overview
The Opportunity object represents a deal in progress (potential sale) in Salesforce.

**HubSpot Equivalent:** Deals

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
https://{instance_url}/services/data/v65.0/sobjects/Opportunity
```

---

## 1. CREATE Opportunity

### Endpoint
```
POST /services/data/v65.0/sobjects/Opportunity
```

### Request Body (JSON Payload)
```json
{
  "Name": "Acme Corp - Enterprise License",
  "AccountId": "0011234567890ABC",
  "Amount": 50000,
  "CloseDate": "2025-03-31",
  "StageName": "Prospecting",
  "Probability": 10,
  "Type": "New Business",
  "LeadSource": "Web",
  "Description": "Enterprise license deal for 500 users",
  "NextStep": "Schedule discovery call"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "0061234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields
- **Name** (opportunity name)
- **StageName** (current stage in sales pipeline)
- **CloseDate** (expected close date)

**Note:** Some orgs may also require **AccountId** depending on validation rules.

---

## 2. READ Opportunity (Get by ID)

### Endpoint
```
GET /services/data/v65.0/sobjects/Opportunity/{opportunity_id}
```

### Response (Success - 200 OK)
```json
{
  "attributes": {
    "type": "Opportunity",
    "url": "/services/data/v65.0/sobjects/Opportunity/0061234567890ABC"
  },
  "Id": "0061234567890ABC",
  "Name": "Acme Corp - Enterprise License",
  "AccountId": "0011234567890ABC",
  "Amount": 50000,
  "CloseDate": "2025-03-31",
  "StageName": "Prospecting",
  "Probability": 10,
  "Type": "New Business",
  "IsClosed": false,
  "IsWon": false,
  "CreatedDate": "2025-01-15T10:30:00.000+0000",
  "LastModifiedDate": "2025-01-15T10:30:00.000+0000"
}
```

---

## 3. SEARCH Opportunity (SOQL Query)

### Search by Account
```
GET /services/data/v65.0/query?q=SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity WHERE AccountId = '0011234567890ABC'
```

### Search Open Opportunities
```
SELECT Id, Name, Amount, StageName, CloseDate 
FROM Opportunity 
WHERE IsClosed = false 
ORDER BY CloseDate ASC
```

### Response
```json
{
  "totalSize": 3,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Opportunity",
        "url": "/services/data/v65.0/sobjects/Opportunity/0061234567890ABC"
      },
      "Id": "0061234567890ABC",
      "Name": "Acme Corp - Enterprise License",
      "Amount": 50000,
      "StageName": "Prospecting",
      "CloseDate": "2025-03-31"
    }
  ]
}
```

---

## 4. UPDATE Opportunity

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Opportunity/{opportunity_id}
```

### Request Body
```json
{
  "StageName": "Qualification",
  "Probability": 25,
  "Amount": 55000,
  "NextStep": "Send proposal"
}
```

### Response (Success - 204 No Content)

---

## 5. DELETE Opportunity

### Endpoint
```
DELETE /services/data/v65.0/sobjects/Opportunity/{opportunity_id}
```

### Response (Success - 204 No Content)

---

## Python Example

```python
import requests
from datetime import datetime, timedelta

instance_url = "https://yourinstance.my.salesforce.com"
access_token = "YOUR_ACCESS_TOKEN"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Create Opportunity
def create_opportunity(name, account_id, amount, stage="Prospecting"):
    url = f"{instance_url}/services/data/v65.0/sobjects/Opportunity"
    
    # Default close date: 90 days from now
    close_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    
    payload = {
        "Name": name,
        "AccountId": account_id,
        "Amount": amount,
        "CloseDate": close_date,
        "StageName": stage
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Update Opportunity Stage
def update_opportunity_stage(opp_id, new_stage, probability=None):
    url = f"{instance_url}/services/data/v65.0/sobjects/Opportunity/{opp_id}"
    
    updates = {"StageName": new_stage}
    if probability is not None:
        updates["Probability"] = probability
    
    response = requests.patch(url, json=updates, headers=headers)
    return response.status_code == 204

# Get Open Opportunities
def get_open_opportunities():
    query = "SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity WHERE IsClosed = false ORDER BY CloseDate ASC"
    url = f"{instance_url}/services/data/v65.0/query"
    params = {"q": query}
    
    response = requests.get(url, params=params, headers=headers)
    return response.json()["records"]

# Close Opportunity as Won
def close_opportunity_won(opp_id):
    return update_opportunity_stage(opp_id, "Closed Won", 100)

# Close Opportunity as Lost
def close_opportunity_lost(opp_id):
    return update_opportunity_stage(opp_id, "Closed Lost", 0)

# Usage
result = create_opportunity(
    name="Acme Corp - Enterprise License",
    account_id="0011234567890ABC",
    amount=50000
)
print(f"Created Opportunity ID: {result['id']}")

# Move to next stage
update_opportunity_stage(result['id'], "Qualification", 25)

# Close as won
close_opportunity_won(result['id'])
```

---

## Common Field Reference

| Field API Name | Type | Description | Required |
|----------------|------|-------------|----------|
| Name | String(120) | Opportunity name | Yes |
| StageName | Picklist | Current stage in sales process | Yes |
| CloseDate | Date | Expected close date | Yes |
| AccountId | Reference | Associated Account ID | Varies* |
| Amount | Currency | Deal amount | No |
| Probability | Percent | Win probability (0-100) | No |
| Type | Picklist | Opportunity type | No |
| LeadSource | Picklist | Original lead source | No |
| NextStep | String(255) | Next action to take | No |
| Description | Textarea | Opportunity description | No |
| IsClosed | Boolean | Whether opp is closed | Read-Only |
| IsWon | Boolean | Whether opp is won | Read-Only |
| ForecastCategory | Picklist | Forecast category | Auto-calculated |
| ForecastCategoryName | String | Forecast category name | Read-Only |
| OwnerId | Reference | Opportunity owner (user) ID | No |
| Pricebook2Id | Reference | Price book ID | No |
| CampaignId | Reference | Primary campaign source | No |

*Depends on org validation rules

---

## Standard Sales Stage Values

Standard stages (varies by org):
1. **Prospecting** (Probability: 10%)
2. **Qualification** (Probability: 25%)
3. **Needs Analysis** (Probability: 40%)
4. **Value Proposition** (Probability: 50%)
5. **Id. Decision Makers** (Probability: 60%)
6. **Perception Analysis** (Probability: 70%)
7. **Proposal/Price Quote** (Probability: 75%)
8. **Negotiation/Review** (Probability: 90%)
9. **Closed Won** (Probability: 100%) ✅
10. **Closed Lost** (Probability: 0%) ❌

**Note:** Stage names and probabilities can be customized per org.

---

## Opportunity Type Picklist Values

- New Business
- Existing Business
- Renewal

---

## Forecast Category Values

- Pipeline
- Best Case
- Commit
- Omitted
- Closed

**Note:** Auto-calculated based on StageName probability.

---

## cURL Examples

### Create Opportunity
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Opportunity" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "Acme Corp - Enterprise License",
    "AccountId": "0011234567890ABC",
    "Amount": 50000,
    "CloseDate": "2025-03-31",
    "StageName": "Prospecting"
  }'
```

### Update Stage
```bash
curl -X PATCH "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Opportunity/0061234567890ABC" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "StageName": "Qualification",
    "Probability": 25
  }'
```

### Get Open Opportunities
```bash
curl -X GET "https://yourinstance.my.salesforce.com/services/data/v65.0/query?q=SELECT+Id,Name,Amount,StageName+FROM+Opportunity+WHERE+IsClosed=false" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Best Practices

1. **Always associate with Account** - Set AccountId for better reporting
2. **Use realistic Close Dates** - Update as deal progresses
3. **Update Amount** as deal scope changes
4. **Use standard Stage Names** - Don't skip stages
5. **Set Next Step** for every opportunity to maintain momentum
6. **Use Campaign attribution** - Set CampaignId for marketing ROI
7. **Track Products** - Use OpportunityLineItems for multi-product deals
8. **Update regularly** - Keep stage and probability current

---

## Sales Process Best Practices

1. Move opportunities through stages sequentially
2. Update Probability as stage changes (usually auto-calculated)
3. Set realistic Close Dates and update quarterly
4. Use NextStep to keep team aligned
5. Associate with Contacts using OpportunityContactRole
6. Track competitors and partners
7. Use forecast categories for pipeline management

---

## Next Steps

- See [Account API Documentation](./02_account.md) to link opportunities
- See [OpportunityLineItem API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_basic_info.htm) for products
- See [OpportunityContactRole API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_basic_info.htm) for contacts
