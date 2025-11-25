# Salesforce REST API - Account Object

## Overview
The Account object represents a company or organization (customer, partner, competitor, etc.) in Salesforce.

**HubSpot Equivalent:** Companies

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
https://{instance_url}/services/data/v65.0/sobjects/Account
```

---

## 1. CREATE Account

### Endpoint
```
POST /services/data/v65.0/sobjects/Account
```

### Request Body (JSON Payload)
```json
{
  "Name": "Acme Corporation",
  "Website": "https://www.acme.com",
  "Phone": "+1-555-100-2000",
  "Industry": "Technology",
  "Type": "Customer",
  "NumberOfEmployees": 500,
  "AnnualRevenue": 5000000,
  "BillingStreet": "500 Market St",
  "BillingCity": "San Francisco",
  "BillingState": "CA",
  "BillingPostalCode": "94105",
  "BillingCountry": "USA",
  "ShippingStreet": "500 Market St",
  "ShippingCity": "San Francisco",
  "ShippingState": "CA",
  "ShippingPostalCode": "94105",
  "ShippingCountry": "USA",
  "Description": "Leading technology company"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "0011234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields
- **Name** (company name - minimum required)

---

## 2. READ Account (Get by ID)

### Endpoint
```
GET /services/data/v65.0/sobjects/Account/{account_id}
```

### Response (Success - 200 OK)
```json
{
  "attributes": {
    "type": "Account",
    "url": "/services/data/v65.0/sobjects/Account/0011234567890ABC"
  },
  "Id": "0011234567890ABC",
  "Name": "Acme Corporation",
  "Website": "https://www.acme.com",
  "Phone": "+1-555-100-2000",
  "Industry": "Technology",
  "Type": "Customer",
  "NumberOfEmployees": 500,
  "AnnualRevenue": 5000000,
  "CreatedDate": "2025-01-15T10:30:00.000+0000"
}
```

---

## 3. SEARCH Account (SOQL Query)

### Search by Name
```
GET /services/data/v65.0/query?q=SELECT Id, Name, Website FROM Account WHERE Name = 'Acme Corporation' LIMIT 1
```

### Search by Website Domain
```
SELECT Id, Name, Website FROM Account WHERE Website LIKE '%acme.com%' LIMIT 1
```

### Response
```json
{
  "totalSize": 1,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Account",
        "url": "/services/data/v65.0/sobjects/Account/0011234567890ABC"
      },
      "Id": "0011234567890ABC",
      "Name": "Acme Corporation",
      "Website": "https://www.acme.com"
    }
  ]
}
```

---

## 4. UPDATE Account

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Account/{account_id}
```

### Request Body
```json
{
  "Phone": "+1-555-999-3000",
  "NumberOfEmployees": 750,
  "AnnualRevenue": 7500000,
  "Industry": "Software"
}
```

### Response (Success - 204 No Content)

---

## 5. DELETE Account

### Endpoint
```
DELETE /services/data/v65.0/sobjects/Account/{account_id}
```

### Response (Success - 204 No Content)

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

# Create Account
def create_account(name, website=None, industry=None):
    url = f"{instance_url}/services/data/v65.0/sobjects/Account"
    payload = {"Name": name}
    
    if website:
        payload["Website"] = website
    if industry:
        payload["Industry"] = industry
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Search Account by Name
def search_account_by_name(name):
    query = f"SELECT Id, Name, Website FROM Account WHERE Name = '{name}' LIMIT 1"
    url = f"{instance_url}/services/data/v65.0/query"
    params = {"q": query}
    
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    
    if data["totalSize"] > 0:
        return data["records"][0]
    return None

# Update Account
def update_account(account_id, updates):
    url = f"{instance_url}/services/data/v65.0/sobjects/Account/{account_id}"
    response = requests.patch(url, json=updates, headers=headers)
    return response.status_code == 204

# Upsert Pattern (Search first, then create or update)
def upsert_account(name, website=None):
    existing = search_account_by_name(name)
    
    if existing:
        # Update existing account
        updates = {}
        if website:
            updates["Website"] = website
        update_account(existing["Id"], updates)
        return existing["Id"]
    else:
        # Create new account
        result = create_account(name, website)
        return result["id"]
```

---

## Common Field Reference

| Field API Name | Type | Description | Required |
|----------------|------|-------------|----------|
| Name | String(255) | Account name | Yes |
| Website | URL | Company website | No |
| Phone | Phone | Main phone number | No |
| Industry | Picklist | Industry type | No |
| Type | Picklist | Account type (Customer, Partner, etc.) | No |
| NumberOfEmployees | Number | Employee count | No |
| AnnualRevenue | Currency | Annual revenue in USD | No |
| BillingStreet | Textarea | Billing street address | No |
| BillingCity | String(40) | Billing city | No |
| BillingState | String(80) | Billing state/province | No |
| BillingPostalCode | String(20) | Billing ZIP/postal code | No |
| BillingCountry | String(80) | Billing country | No |
| ShippingStreet | Textarea | Shipping street address | No |
| ShippingCity | String(40) | Shipping city | No |
| ShippingState | String(80) | Shipping state/province | No |
| ShippingPostalCode | String(20) | Shipping ZIP/postal code | No |
| ShippingCountry | String(80) | Shipping country | No |
| Description | Textarea | Account description | No |
| ParentId | Reference | Parent Account ID | No |
| OwnerId | Reference | Account owner (user) ID | No |

---

## Industry Picklist Values

Common industry values:
- Agriculture
- Apparel
- Banking
- Biotechnology
- Chemicals
- Communications
- Construction
- Consulting
- Education
- Electronics
- Energy
- Engineering
- Entertainment
- Environmental
- Finance
- Food & Beverage
- Government
- Healthcare
- Hospitality
- Insurance
- Machinery
- Manufacturing
- Media
- Not For Profit
- Recreation
- Retail
- Shipping
- Technology
- Telecommunications
- Transportation
- Utilities
- Other

---

## Account Type Picklist Values

- Customer - Direct
- Customer - Channel
- Channel Partner / Reseller
- Installation Partner
- Technology Partner
- Other

---

## cURL Examples

### Create Account
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Account" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "Acme Corporation",
    "Website": "https://www.acme.com",
    "Industry": "Technology",
    "NumberOfEmployees": 500
  }'
```

### Search by Name
```bash
curl -X GET "https://yourinstance.my.salesforce.com/services/data/v65.0/query?q=SELECT+Id,Name,Website+FROM+Account+WHERE+Name='Acme+Corporation'+LIMIT+1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Best Practices

1. **Use unique identifiers** like Website or external ID for deduplication
2. **Always check for existing accounts** before creating (search by name or website)
3. **Associate Contacts with Accounts** using Contact.AccountId
4. **Use ParentId** to create account hierarchies
5. **Populate address fields** for better data quality
6. **Set proper Account Type** for reporting and automation

---

## Next Steps

- See [Contact API Documentation](./01_contact.md) to associate contacts with this account
- See [Opportunity API Documentation](./04_opportunity.md) to create deals for this account
