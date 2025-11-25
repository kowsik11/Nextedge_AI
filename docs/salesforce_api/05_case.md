# Salesforce REST API - Case Object

## Overview
The Case object represents a customer support issue or ticket in Salesforce.

**HubSpot Equivalent:** Tickets

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
https://{instance_url}/services/data/v65.0/sobjects/Case
```

---

## 1. CREATE Case

### Endpoint
```
POST /services/data/v65.0/sobjects/Case
```

### Request Body (JSON Payload)
```json
{
  "Subject": "Cannot access dashboard",
  "Description": "User reports error 500 when trying to access the main dashboard. Occurs after recent update.",
  "Status": "New",
  "Priority": "High",
  "Origin": "Email",
  "Type": "Problem",
  "Reason": "Performance",
  "ContactId": "0031234567890ABC",
  "AccountId": "0011234567890ABC",
  "SuppliedEmail": "john.doe@example.com",
  "SuppliedName": "John Doe",
  "SuppliedPhone": "+1-555-123-4567"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "5001234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields
None are strictly required at the API level, but most orgs require:
- **Subject** (case subject)
- **Status** (case status - defaults to "New")

---

## 2. READ Case (Get by ID)

### Endpoint
```
GET /services/data/v65.0/sobjects/Case/{case_id}
```

### Response (Success - 200 OK)
```json
{
  "attributes": {
    "type": "Case",
    "url": "/services/data/v65.0/sobjects/Case/5001234567890ABC"
  },
  "Id": "5001234567890ABC",
  "CaseNumber": "00001234",
  "Subject": "Cannot access dashboard",
  "Description": "User reports error 500...",
  "Status": "New",
  "Priority": "High",
  "Origin": "Email",
  "Type": "Problem",
  "Reason": "Performance",
  "ContactId": "0031234567890ABC",
  "AccountId": "0011234567890ABC",
  "IsClosed": false,
  "IsEscalated": false,
  "CreatedDate": "2025-01-15T10:30:00.000+0000",
  "LastModifiedDate": "2025-01-15T10:30:00.000+0000"
}
```

---

## 3. SEARCH Case (SOQL Query)

### Search by Contact
```
GET /services/data/v65.0/query?q=SELECT Id, CaseNumber, Subject, Status, Priority FROM Case WHERE ContactId = '0031234567890ABC'
```

### Search Open Cases
```
SELECT Id, CaseNumber, Subject, Status, Priority, CreatedDate 
FROM Case 
WHERE IsClosed = false 
ORDER BY Priority DESC, CreatedDate ASC
```

### Response
```json
{
  "totalSize": 5,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Case",
        "url": "/services/data/v65.0/sobjects/Case/5001234567890ABC"
      },
      "Id": "5001234567890ABC",
      "CaseNumber": "00001234",
      "Subject": "Cannot access dashboard",
      "Status": "New",
      "Priority": "High",
      "CreatedDate": "2025-01-15T10:30:00.000+0000"
    }
  ]
}
```

---

## 4. UPDATE Case

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Case/{case_id}
```

### Request Body
```json
{
  "Status": "Working",
  "Priority": "Medium",
  "OwnerId": "0051234567890ABC",
  "Description": "Updated: User reports error 500 when trying to access the main dashboard. Occurs after recent update. \n\nUpdate: Investigated issue, appears to be cache related."
}
```

### Response (Success - 204 No Content)

---

## 5. CLOSE Case

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Case/{case_id}
```

### Request Body
```json
{
  "Status": "Closed",
  "Resolution": "Cleared browser cache and session cookies. Issue resolved."
}
```

### Response (Success - 204 No Content)

---

## 6. DELETE Case

### Endpoint
```
DELETE /services/data/v65.0/sobjects/Case/{case_id}
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

# Create Case
def create_case(subject, description, priority="Medium", contact_id=None, account_id=None):
    url = f"{instance_url}/services/data/v65.0/sobjects/Case"
    
    payload = {
        "Subject": subject,
        "Description": description,
        "Status": "New",
        "Priority": priority,
        "Origin": "Web"
    }
    
    if contact_id:
        payload["ContactId"] = contact_id
    if account_id:
        payload["AccountId"] = account_id
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Update Case Status
def update_case_status(case_id, new_status):
    url = f"{instance_url}/services/data/v65.0/sobjects/Case/{case_id}"
    payload = {"Status": new_status}
    
    response = requests.patch(url, json=payload, headers=headers)
    return response.status_code == 204

# Close Case
def close_case(case_id, resolution):
    url = f"{instance_url}/services/data/v65.0/sobjects/Case/{case_id}"
    payload = {
        "Status": "Closed",
        "Resolution": resolution
    }
    
    response = requests.patch(url, json=payload, headers=headers)
    return response.status_code == 204

# Get Open Cases for Contact
def get_open_cases_for_contact(contact_id):
    query = f"SELECT Id, CaseNumber, Subject, Status, Priority FROM Case WHERE ContactId = '{contact_id}' AND IsClosed = false"
    url = f"{instance_url}/services/data/v65.0/query"
    params = {"q": query}
    
    response = requests.get(url, params=params, headers=headers)
    return response.json()["records"]

# Usage
result = create_case(
    subject="Cannot access dashboard",
    description="User reports error 500 when accessing dashboard",
    priority="High",
    contact_id="0031234567890ABC",
    account_id="0011234567890ABC"
)
case_id = result["id"]
print(f"Created Case ID: {case_id}")

# Update status
update_case_status(case_id, "Working")

# Close case
close_case(case_id, "Issue resolved - cleared cache")
```

---

## Common Field Reference

| Field API Name | Type | Description | Required |
|----------------|------|-------------|----------|
| Subject | String(255) | Case subject/title | No* |
| Description | Textarea | Case details | No |
| Status | Picklist | Current status | No** |
| Priority | Picklist | Priority level | No |
| Origin | Picklist | How case was created | No |
| Type | Picklist | Case type | No |
| Reason | Picklist | Case reason | No |
| ContactId | Reference | Related Contact ID | No |
| AccountId | Reference | Related Account ID | No |
| CaseNumber | Auto Number | Auto-generated case number | Read-Only |
| IsClosed | Boolean | Whether case is closed | Read-Only |
| IsEscalated | Boolean | Whether case is escalated | No |
| ClosedDate | DateTime | Date case was closed | Read-Only |
| OwnerId | Reference | Case owner (user/queue) ID | No |
| SuppliedEmail | Email | Email from external source | No |
| SuppliedName | String(80) | Name from external source | No |
| SuppliedPhone | Phone | Phone from external source | No |
| SuppliedCompany | String(80) | Company from external source | No |
| Resolution | Textarea | Resolution description | No |
| ParentId | Reference | Parent Case ID (for case escalation) | No |

* Required in most orgs via validation rules
** Defaults to "New"

---

## Case Status Picklist Values

Standard statuses:
- **New** - Just created
- **Working** - Being investigated
- **Escalated** - Escalated to higher tier
- **Closed** - Resolved and closed

**Note:** Can be customized per org

---

## Case Priority Picklist Values

- **Low**
- **Medium**
- **High**
- **Critical**

---

## Case Origin Picklist Values

- **Web**
- **Phone**
- **Email**
- **Chat**
- **Social Media**
- **Other**

---

## Case Type Picklist Values

- **Problem**
- **Question**
- **Feature Request**
- **Other**

---

## cURL Examples

### Create Case
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Case" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Subject": "Cannot access dashboard",
    "Description": "User reports error 500",
    "Status": "New",
    "Priority": "High",
    "Origin": "Email",
    "ContactId": "0031234567890ABC"
  }'
```

### Update Case
```bash
curl -X PATCH "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Case/5001234567890ABC" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Status": "Working",
    "Priority": "Medium"
  }'
```

### Close Case
```bash
curl -X PATCH "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Case/5001234567890ABC" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Status": "Closed",
    "Resolution": "Issue resolved - cleared cache"
  }'
```

---

## Best Practices

1. **Always set Subject** - Required for identifying cases
2. **Link to Contact/Account** - Set ContactId and AccountId for context
3. **Set appropriate Priority** - Use priority for SLA routing
4. **Use proper Origin** - Track where cases come from
5. **Update Status regularly** - Keep customers informed
6. **Document Resolution** - Fill Resolution field when closing
7. **Use Case Comments** - Add CaseComments for communication history
8. **Auto-assign with queues** - Use ownership queues for routing
9. **Escalate when needed** - Set IsEscalated = true for urgent cases
10. **Track metrics** - Use IsClosed, ClosedDate for reporting

---

## Support Process Best Practices

1. Create cases with all available context (email, phone, etc.)
2. Set realistic priorities based on impact
3. Assign to appropriate owner or queue
4. Update status as work progresses
5. Add comments for internal collaboration
6. Document resolution thoroughly
7. Close cases only when fully resolved
8. Use case escalation for complex issues
9. Link related cases using ParentId
10. Track customer satisfaction

---

## Next Steps

- See [Contact API Documentation](./01_contact.md) to link cases to contacts
- See [Account API Documentation](./02_account.md) to link cases to accounts
- Add Case Comments using CaseComment object
- Set up Email-to-Case for automatic case creation
