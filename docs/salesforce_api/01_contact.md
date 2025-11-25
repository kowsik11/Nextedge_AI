# Salesforce REST API - Contact Object

## Overview
The Contact object represents an individual person associated with an Account in Salesforce.

**HubSpot Equivalent:** Contacts

---

## Authentication

All Salesforce REST API requests require OAuth 2.0 authentication.

**Required Headers:**
```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

---

## Base URL Pattern
```
https://{instance_url}/services/data/v65.0/sobjects/Contact
```

Replace `{instance_url}` with your Salesforce instance URL (e.g., `https://yourinstance.my.salesforce.com`)

---

## 1. CREATE Contact

### Endpoint
```
POST /services/data/v65.0/sobjects/Contact
```

### Request Headers
```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

### Request Body (JSON Payload)
```json
{
  "FirstName": "John",
  "LastName": "Doe",
  "Email": "john.doe@example.com",
  "Phone": "+1-555-123-4567",
  "Title": "Software Engineer",
  "Department": "Engineering",
  "AccountId": "0011234567890ABC",
  "MailingStreet": "123 Main St",
  "MailingCity": "San Francisco",
  "MailingState": "CA",
  "MailingPostalCode": "94102",
  "MailingCountry": "USA",
  "Description": "Contact created via REST API"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "0031234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields
- **LastName** (minimum required field)

### Optional Important Fields
- FirstName
- Email
- Phone
- AccountId (to associate with a company)
- Title
- Department
- MailingAddress fields
- Description

---

## 2. READ Contact (Get by ID)

### Endpoint
```
GET /services/data/v65.0/sobjects/Contact/{contact_id}
```

### Example
```
GET /services/data/v65.0/sobjects/Contact/0031234567890ABC
```

### Response (Success - 200 OK)
```json
{
  "attributes": {
    "type": "Contact",
    "url": "/services/data/v65.0/sobjects/Contact/0031234567890ABC"
  },
  "Id": "0031234567890ABC",
  "FirstName": "John",
  "LastName": "Doe",
  "Email": "john.doe@example.com",
  "Phone": "+1-555-123-4567",
  "Title": "Software Engineer",
  "Department": "Engineering",
  "AccountId": "0011234567890ABC",
  "CreatedDate": "2025-01-15T10:30:00.000+0000",
  "LastModifiedDate": "2025-01-15T10:30:00.000+0000"
}
```

---

## 3. SEARCH Contact (SOQL Query)

### Endpoint
```
GET /services/data/v65.0/query?q={SOQL_QUERY}
```

### Search by Email Example
```
GET /services/data/v65.0/query?q=SELECT Id, FirstName, LastName, Email FROM Contact WHERE Email = 'john.doe@example.com' LIMIT 1
```

### URL-Encoded Query
```
GET /services/data/v65.0/query?q=SELECT+Id,FirstName,LastName,Email+FROM+Contact+WHERE+Email='john.doe@example.com'+LIMIT+1
```

### Response (Success - 200 OK)
```json
{
  "totalSize": 1,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Contact",
        "url": "/services/data/v65.0/sobjects/Contact/0031234567890ABC"
      },
      "Id": "0031234567890ABC",
      "FirstName": "John",
      "LastName": "Doe",
      "Email": "john.doe@example.com"
    }
  ]
}
```

---

## 4. UPDATE Contact

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Contact/{contact_id}
```

### Request Headers
```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

### Request Body (JSON Payload)
```json
{
  "Phone": "+1-555-999-8888",
  "Title": "Senior Software Engineer",
  "Department": "Product Engineering"
}
```

### Response (Success - 204 No Content)
No body returned on successful update.

---

## 5. DELETE Contact

### Endpoint
```
DELETE /services/data/v65.0/sobjects/Contact/{contact_id}
```

### Example
```
DELETE /services/data/v65.0/sobjects/Contact/0031234567890ABC
```

### Response (Success - 204 No Content)
No body returned on successful deletion.

---

## Complete cURL Examples

### Create Contact
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Contact" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "FirstName": "John",
    "LastName": "Doe",
    "Email": "john.doe@example.com",
    "Phone": "+1-555-123-4567"
  }'
```

### Search Contact by Email
```bash
curl -X GET "https://yourinstance.my.salesforce.com/services/data/v65.0/query?q=SELECT+Id,FirstName,LastName,Email+FROM+Contact+WHERE+Email='john.doe@example.com'+LIMIT+1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Contact
```bash
curl -X PATCH "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Contact/0031234567890ABC" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Phone": "+1-555-999-8888",
    "Title": "Senior Software Engineer"
  }'
```

---

## Python Example (Using Requests)

```python
import requests

# Authentication
instance_url = "https://yourinstance.my.salesforce.com"
access_token = "YOUR_ACCESS_TOKEN"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Create Contact
def create_contact(first_name, last_name, email):
    url = f"{instance_url}/services/data/v65.0/sobjects/Contact"
    payload = {
        "FirstName": first_name,
        "LastName": last_name,
        "Email": email
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Search Contact by Email
def search_contact_by_email(email):
    query = f"SELECT Id, FirstName, LastName, Email FROM Contact WHERE Email = '{email}' LIMIT 1"
    url = f"{instance_url}/services/data/v65.0/query"
    params = {"q": query}
    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    if data["totalSize"] > 0:
        return data["records"][0]
    return None

# Update Contact
def update_contact(contact_id, updates):
    url = f"{instance_url}/services/data/v65.0/sobjects/Contact/{contact_id}"
    response = requests.patch(url, json=updates, headers=headers)
    return response.status_code == 204

# Usage
result = create_contact("John", "Doe", "john.doe@example.com")
print(f"Created Contact ID: {result['id']}")

contact = search_contact_by_email("john.doe@example.com")
if contact:
    print(f"Found Contact: {contact['Id']}")
    
success = update_contact(contact['Id'], {"Phone": "+1-555-999-8888"})
print(f"Update successful: {success}")
```

---

## Common Field Reference

| Field API Name | Type | Description | Required |
|----------------|------|-------------|----------|
| LastName | String(80) | Contact's last name | Yes |
| FirstName | String(40) | Contact's first name | No |
| Email | Email | Contact's email address | No |
| Phone | Phone | Contact's phone number | No |
| MobilePhone | Phone | Contact's mobile phone | No |
| Title | String(128) | Contact's title/position | No |
| Department | String(80) | Department name | No |
| AccountId | Reference | ID of associated Account | No |
| MailingStreet | Textarea | Mailing street address | No |
| MailingCity | String(40) | Mailing city | No |
| MailingState | String(80) | Mailing state/province | No |
| MailingPostalCode | String(20) | Mailing ZIP/postal code | No |
| MailingCountry | String(80) | Mailing country | No |
| Description | Textarea | Additional details | No |
| Birthdate | Date | Contact's birthday | No |
| LeadSource | Picklist | How the contact was acquired | No |

---

## Error Handling

### Common Error Responses

**400 Bad Request - Missing Required Field:**
```json
[
  {
    "message": "Required fields are missing: [LastName]",
    "errorCode": "REQUIRED_FIELD_MISSING",
    "fields": ["LastName"]
  }
]
```

**401 Unauthorized - Invalid Token:**
```json
[
  {
    "message": "Session expired or invalid",
    "errorCode": "INVALID_SESSION_ID"
  }
]
```

**404 Not Found - Contact Doesn't Exist:**
```json
[
  {
    "message": "The requested resource does not exist",
    "errorCode": "NOT_FOUND"
  }
]
```

---

## Best Practices

1. **Always validate email before creating** to avoid duplicates
2. **Search first, then create or update** (upsert pattern)
3. **Use external ID fields** for integration scenarios
4. **Associate with Account** whenever possible using AccountId
5. **Handle errors gracefully** and implement retry logic
6. **Respect API rate limits** (15,000 calls per 24 hours for most orgs)
7. **Use bulk APIs** for processing > 200 records

---

## Next Steps

- See [Account API Documentation](./02_account.md) for company/organization records
- See [Lead API Documentation](./03_lead.md) for prospective customers
