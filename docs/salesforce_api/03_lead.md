# Salesforce REST API - Lead Object

## Overview
The Lead object represents a prospective customer/company before qualification. Leads can be converted to Contacts, Accounts, and Opportunities.

**HubSpot Equivalent:** *No direct equivalent - Leads convert to Contact/Account*

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
https://{instance_url}/services/data/v65.0/sobjects/Lead
```

---

## 1. CREATE Lead

### Endpoint
```
POST /services/data/v65.0/sobjects/Lead
```

### Request Body (JSON Payload)
```json
{
  "FirstName": "Jane",
  "LastName": "Smith",
  "Company": "Smith Enterprises",
  "Email": "jane.smith@smithent.com",
  "Phone": "+1-555-200-3000",
  "Title": "CEO",
  "Industry": "Technology",
  "LeadSource": "Web",
  "Status": "Open - Not Contacted",
  "Rating": "Hot",
  "Street": "100 Innovation Drive",
  "City": "Austin",
  "State": "TX",
  "PostalCode": "78701",
  "Country": "USA",
  "Description": "Interested in enterprise solutions"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "00Q1234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields
- **LastName** (person's last name)
- **Company** (company name)

---

## 2. READ Lead (Get by ID)

### Endpoint
```
GET /services/data/v65.0/sobjects/Lead/{lead_id}
```

### Response (Success - 200 OK)
```json
{
  "attributes": {
    "type": "Lead",
    "url": "/services/data/v65.0/sobjects/Lead/00Q1234567890ABC"
  },
  "Id": "00Q1234567890ABC",
  "FirstName": "Jane",
  "LastName": "Smith",
  "Company": "Smith Enterprises",
  "Email": "jane.smith@smithent.com",
  "Status": "Open - Not Contacted",
  "Rating": "Hot",
  "IsConverted": false,
  "CreatedDate": "2025-01-15T10:30:00.000+0000"
}
```

---

## 3. SEARCH Lead (SOQL Query)

### Search by Email
```
GET /services/data/v65.0/query?q=SELECT Id, FirstName, LastName, Company, Email, Status FROM Lead WHERE Email = 'jane.smith@smithent.com' LIMIT 1
```

### Response
```json
{
  "totalSize": 1,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Lead",
        "url": "/services/data/v65.0/sobjects/Lead/00Q1234567890ABC"
      },
      "Id": "00Q1234567890ABC",
      "FirstName": "Jane",
      "LastName": "Smith",
      "Company": "Smith Enterprises",
      "Email": "jane.smith@smithent.com",
      "Status": "Open - Not Contacted"
    }
  ]
}
```

---

## 4. UPDATE Lead

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Lead/{lead_id}
```

### Request Body
```json
{
  "Status": "Working - Contacted",
  "Rating": "Warm",
  "Phone": "+1-555-200-3001"
}
```

### Response (Success - 204 No Content)

---

## 5. CONVERT Lead

### Endpoint
```
POST /services/data/v65.0/sobjects/Lead/{lead_id}/convert
```

### Request Body (JSON Payload)
```json
{
  "leadId": "00Q1234567890ABC",
  "convertedStatus": "Qualified",
  "createOpportunity": true,
  "opportunityName": "Smith Enterprises - New Deal",
  "doNotCreateOpportunity": false,
  "sendNotificationEmail": false,
  "overwriteLeadSource": false
}
```

### Response (Success - 200 OK)
```json
{
  "leadId": "00Q1234567890ABC",
  "contactId": "0031234567890XYZ",
  "accountId": "0011234567890XYZ",
  "opportunityId": "0061234567890XYZ",
  "success": true,
  "errors": []
}
```

### Convert Options
- **createOpportunity** (boolean) - Create an Opportunity during conversion
- **opportunityName** (string) - Name of the opportunity (if createOpportunity = true)
- **accountId** (string) - Existing Account ID to associate (optional)
- **contactId** (string) - Existing Contact ID to associate (optional)
- **convertedStatus** (string) - Status value for converted lead (must be a valid converted status)

---

## 6. DELETE Lead

### Endpoint
```
DELETE /services/data/v65.0/sobjects/Lead/{lead_id}
```

### Response (Success - 204 No Content)

**Note:** Converted Leads cannot be deleted.

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

# Create Lead
def create_lead(first_name, last_name, company, email):
    url = f"{instance_url}/services/data/v65.0/sobjects/Lead"
    payload = {
        "FirstName": first_name,
        "LastName": last_name,
        "Company": company,
        "Email": email,
        "Status": "Open - Not Contacted"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Convert Lead to Contact/Account/Opportunity
def convert_lead(lead_id, create_opportunity=True, opportunity_name=None):
    url = f"{instance_url}/services/data/v65.0/sobjects/Lead/{lead_id}/convert"
    payload = {
        "leadId": lead_id,
        "convertedStatus": "Qualified",
        "createOpportunity": create_opportunity,
        "sendNotificationEmail": False
    }
    
    if create_opportunity and opportunity_name:
        payload["opportunityName"] = opportunity_name
    else:
        payload["doNotCreateOpportunity"] = True
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Usage
result = create_lead("Jane", "Smith", "Smith Enterprises", "jane@smithent.com")
lead_id = result["id"]
print(f"Created Lead ID: {lead_id}")

# Convert Lead
converted = convert_lead(lead_id, True, "Smith Enterprises - New Deal")
print(f"Contact ID: {converted['contactId']}")
print(f"Account ID: {converted['accountId']}")
print(f"Opportunity ID: {converted['opportunityId']}")
```

---

## Common Field Reference

| Field API Name | Type | Description | Required |
|----------------|------|-------------|----------|
| LastName | String(80) | Lead's last name | Yes |
| FirstName | String(40) | Lead's first name | No |
| Company | String(255) | Company name | Yes |
| Email | Email | Email address | No |
| Phone | Phone | Phone number | No |
| Title | String(128) | Job title | No |
| Industry | Picklist | Industry | No |
| LeadSource | Picklist | Lead source | No |
| Status | Picklist | Lead status | No |
| Rating | Picklist | Lead rating (Hot/Warm/Cold) | No |
| Street | Textarea | Street address | No |
| City | String(40) | City | No |
| State | String(80) | State/Province | No |
| PostalCode | String(20) | ZIP/Postal code | No |
| Country | String(80) | Country | No |
| Description | Textarea | Additional details | No |
| IsConverted | Boolean | Whether lead is converted | Read-Only |
| ConvertedDate | Date | Date lead was converted | Read-Only |
| ConvertedAccountId | Reference | Account created from conversion | Read-Only |
| ConvertedContactId | Reference | Contact created from conversion | Read-Only |
| ConvertedOpportunityId | Reference | Opportunity created from conversion | Read-Only |

---

## Lead Status Picklist Values

Standard statuses (varies by org):
- Open - Not Contacted
- Working - Contacted
- Closed - Converted *(Converted status)*
- Closed - Not Converted

**Note:** At least one status must be marked as "Converted" status in Setup.

---

## Lead Rating Picklist Values

- Hot
- Warm
- Cold

---

## Lead Source Picklist Values

Common values:
- Web
- Phone Inquiry
- Partner Referral
- Purchased List
- Other

---

## cURL Examples

### Create Lead
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Lead" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "FirstName": "Jane",
    "LastName": "Smith",
    "Company": "Smith Enterprises",
    "Email": "jane@smithent.com",
    "Status": "Open - Not Contacted"
  }'
```

### Convert Lead
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Lead/00Q1234567890ABC/convert" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leadId": "00Q1234567890ABC",
    "convertedStatus": "Qualified",
    "createOpportunity": true,
    "opportunityName": "Smith Enterprises - New Deal"
  }'
```

---

## Best Practices

1. **Deduplicate before creating** - Search by email to avoid duplicate leads
2. **Use Lead Source** to track marketing attribution
3. **Set proper Rating** based on qualification criteria
4. **Update Status** as you qualify the lead
5. **Convert when qualified** - Don't let qualified leads sit unconverted
6. **Create Opportunity during conversion** if there's a deal opportunity
7. **Use assignment rules** to route leads to appropriate owners

---

## Lead Conversion Best Practices

1. Always set **convertedStatus** to a valid "Converted" status value
2. **createOpportunity=true** if there's a sales opportunity
3. **Provide opportunityName** when creating opportunity
4. Check if Contact/Account already exists and pass their IDs to avoid duplicates
5. Converted Leads are **read-only** and cannot be edited or deleted

---

## Next Steps

- After conversion, see [Contact API Documentation](./01_contact.md)
- After conversion, see [Account API Documentation](./02_account.md)
- After conversion, see [Opportunity API Documentation](./04_opportunity.md)
