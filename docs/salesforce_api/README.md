# Salesforce REST API Documentation

Complete API documentation for all 7 Salesforce CRM standard objects used in the NextEdge project.

---

## 📚 Documentation Index

| # | CRM Object | HubSpot Equivalent | Documentation File |
|---|------------|-------------------|-------------------|
| 1 | **Contact** | Contacts | [01_contact.md](./01_contact.md) |
| 2 | **Account** | Companies | [02_account.md](./02_account.md) |
| 3 | **Lead** | *(Converts to Contact/Account)* | [03_lead.md](./03_lead.md) |
| 4 | **Opportunity** | Deals | [04_opportunity.md](./04_opportunity.md) |
| 5 | **Case** | Tickets | [05_case.md](./05_case.md) |
| 6 | **Campaign** | *(Marketing Events/Lists)* | [06_campaign.md](./06_campaign.md) |
| 7 | **Order** | Orders | [07_order.md](./07_order.md) |

---

## 🚀 Quick Start

### Authentication

All Salesforce REST API calls require OAuth 2.0 authentication:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

### Base URL Pattern

```
https://{instance_url}/services/data/v65.0/sobjects/{ObjectName}
```

Replace:
- `{instance_url}` with your Salesforce instance (e.g., `https://yourinstance.my.salesforce.com`)
- `{ObjectName}` with the object type (e.g., `Contact`, `Account`, `Lead`)

---

## 📖 What Each Document Contains

Each API documentation file includes:

✅ **CRUD Operations** - Create, Read, Update, Delete examples  
✅ **Headers & Authentication** - Required headers for all requests  
✅ **JSON Payloads** - Complete request/response examples  
✅ **SOQL Queries** - Search and filter examples  
✅ **Field Reference** - All important fields with descriptions  
✅ **Picklist Values** - Standard dropdown values  
✅ **cURL Examples** - Copy-paste terminal commands  
✅ **Python Examples** - Production-ready code snippets  
✅ **Best Practices** - Expert tips and recommendations  
✅ **Error Handling** - Common errors and solutions  

---

## 🎯 Common Use Cases

### Create a Contact
```python
import requests

url = "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Contact"
headers = {
    "Authorization": "Bearer YOUR_ACCESS_TOKEN",
    "Content-Type": "application/json"
}
payload = {
    "FirstName": "John",
    "LastName": "Doe",
    "Email": "john.doe@example.com"
}

response = requests.post(url, json=payload, headers=headers)
contact_id = response.json()["id"]
```

### Search for Account
```python
query = "SELECT Id, Name FROM Account WHERE Name = 'Acme Corp' LIMIT 1"
url = f"https://yourinstance.my.salesforce.com/services/data/v65.0/query?q={query}"

response = requests.get(url, headers=headers)
account = response.json()["records"][0]
```

### Create an Opportunity
```python
url = "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Opportunity"
payload = {
    "Name": "New Deal",
    "AccountId": account["Id"],
    "StageName": "Prospecting",
    "CloseDate": "2025-03-31",
    "Amount": 50000
}

response = requests.post(url, json=payload, headers=headers)
```

---

## 🔗 Object Relationships

### Data Model Overview

```
Lead ──(converts to)──> Contact ──(belongs to)──> Account
                           │                          │
                           │                          │
                           └──────> Case              │
                                     │                 │
                                     │                 └──> Opportunity
                                     │                          │
                                   (belongs to)            (converts to)
                                                              │
                                                              └──> Order
```

### Relationship Guide

- **Contact → Account**: Set `Contact.AccountId`
- **Opportunity → Account**: Set `Opportunity.AccountId`
- **Case → Contact**: Set `Case.ContactId`
- **Case → Account**: Set `Case.AccountId`
- **Order → Account**: Set `Order.AccountId`
- **Lead → Convert**: Creates Contact, Account, and Opportunity
- **Campaign Members**: Link Leads/Contacts to Campaigns

---

## 💡 Best Practices

### 1. Always Search Before Creating
```python
# Bad - Creates duplicates
create_contact("John", "Doe", "john@example.com")

# Good - Check first
existing = search_contact_by_email("john@example.com")
if existing:
    update_contact(existing["Id"], updates)
else:
    create_contact("John", "Doe", "john@example.com")
```

### 2. Handle Errors Gracefully
```python
try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if response.status_code == 401:
        # Refresh access token
        refresh_token()
    elif response.status_code == 400:
        # Handle validation errors
        errors = response.json()
        handle_validation_errors(errors)
```

### 3. Respect API Limits

Salesforce API limits:
- **15,000 API calls per 24 hours** (most orgs)
- **Rate limiting**: Concurrent request limits
- **Bulk API**: Use for > 200 records

### 4. Use Proper Field Names

Always use API names from the documentation:
- ✅ `FirstName`, `LastName`, `Email`
- ❌ `First Name`, `Last Name`, `E-mail`

---

## 🛠️ Integration Patterns

### Upsert Pattern (Recommended)
```python
def upsert_contact(email, updates):
    """Search for contact by email, update if exists, create if not"""
    existing = search_contact_by_email(email)
    
    if existing:
        update_contact(existing["Id"], updates)
        return existing["Id"]
    else:
        updates["Email"] = email
        result = create_contact(updates)
        return result["id"]
```

### Bulk Operations
```python
# For > 200 records, use Composite API
url = f"{instance_url}/services/data/v65.0/composite/sobjects"
payload = {
    "allOrNone": False,
    "records": [
        {"attributes": {"type": "Contact"}, "FirstName": "John", "LastName": "Doe"},
        {"attributes": {"type": "Contact"}, "FirstName": "Jane", "LastName": "Smith"},
        # ... up to 200 records
    ]
}
```

---

## 📝 Common Errors

### 401 Unauthorized
```json
{
  "message": "Session expired or invalid",
  "errorCode": "INVALID_SESSION_ID"
}
```
**Solution:** Refresh your OAuth access token

### 400 Bad Request - Missing Required Field
```json
{
  "message": "Required fields are missing: [LastName]",
  "errorCode": "REQUIRED_FIELD_MISSING",
  "fields": ["LastName"]
}
```
**Solution:** Include all required fields in your payload

### 404 Not Found
```json
{
  "message": "The requested resource does not exist",
  "errorCode": "NOT_FOUND"
}
```
**Solution:** Verify the record ID exists

---

## 🔍 Next Steps

1. **Read the specific object documentation** for detailed examples
2. **Set up OAuth authentication** for your Salesforce instance
3. **Test with cURL** before integrating into your application
4. **Implement error handling** for production use
5. **Monitor API usage** to stay within limits

---

## 📚 Additional Resources

- [Salesforce REST API Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [Salesforce Object Reference](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/)
- [OAuth 2.0 Documentation](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_web_server_flow.htm)
- [SOQL Query Language](https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/)

---

## 📞 Support

For questions about these API docs or Salesforce integration:
1. Check the specific object documentation file
2. Review Salesforce's official API documentation
3. Test with the provided cURL/Python examples

---

**Last Updated:** January 2025  
**API Version:** v65.0  
**Project:** NextEdge CRM Integration
