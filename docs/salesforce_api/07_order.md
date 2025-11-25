# Salesforce REST API - Order Object

## Overview
The Order object represents a purchase order/confirmed sale in Salesforce.

**HubSpot Equivalent:** Orders

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
https://{instance_url}/services/data/v65.0/sobjects/Order
```

**Alternative - Place Order Composite API:**
```
https://{instance_url}/services/data/v65.0/commerce/sale/order
```

---

## 1. CREATE Order

### Endpoint
```
POST /services/data/v65.0/sobjects/Order
```

### Request Body (JSON Payload)
```json
{
  "AccountId": "0011234567890ABC",
  "EffectiveDate": "2025-01-20",
  "Status": "Draft",
  "Pricebook2Id": "01s1234567890ABC",
  "BillingStreet": "123 Main St",
  "BillingCity": "San Francisco",
  "BillingState": "CA",
  "BillingPostalCode": "94102",
  "BillingCountry": "USA",
  "ShippingStreet": "123 Main St",
  "ShippingCity": "San Francisco",
  "ShippingState": "CA",
  "ShippingPostalCode": "94102",
  "ShippingCountry": "USA",
  "BillToContactId": "0031234567890XYZ",
  "ShipToContactId": "0031234567890XYZ",
  "OrderReferenceNumber": "PO-2025-001",
  "Description": "Enterprise license renewal order"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "8011234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields
- **AccountId** (or ContractId)
- **EffectiveDate** (date order becomes effective)
- **Status** (must be "Draft" initially)
- **Pricebook2Id** (reference to price book)*

*Some orgs can enable orders without price books

---

## 2. READ Order (Get by ID)

### Endpoint
```
GET /services/data/v65.0/sobjects/Order/{order_id}
```

### Response (Success - 200 OK)
```json
{
  "attributes": {
    "type": "Order",
    "url": "/services/data/v65.0/sobjects/Order/8011234567890ABC"
  },
  "Id": "8011234567890ABC",
  "OrderNumber": "00000123",
  "AccountId": "0011234567890ABC",
  "EffectiveDate": "2025-01-20",
  "Status": "Draft",
  "TotalAmount": 50000,
  "BillingStreet": "123 Main St",
  "BillingCity": "San Francisco",
  "OrderReferenceNumber": "PO-2025-001",
  "CreatedDate": "2025-01-15T10:30:00.000+0000",
  "LastModifiedDate": "2025-01-15T10:30:00.000+0000"
}
```

---

## 3. SEARCH Order (SOQL Query)

### Get Orders by Account
```
GET /services/data/v65.0/query?q=SELECT Id, OrderNumber, Status, TotalAmount, EffectiveDate FROM Order WHERE AccountId = '0011234567890ABC'
```

### Get Active Orders
```
SELECT Id, OrderNumber, AccountId, Status, TotalAmount, EffectiveDate 
FROM Order 
WHERE Status != 'Draft' 
ORDER BY EffectiveDate DESC
```

### Response
```json
{
  "totalSize": 2,
  "done": true,
  "records": [
    {
      "attributes": {
        "type": "Order",
        "url": "/services/data/v65.0/sobjects/Order/8011234567890ABC"
      },
      "Id": "8011234567890ABC",
      "OrderNumber": "00000123",
      "AccountId": "0011234567890ABC",
      "Status": "Activated",
      "TotalAmount": 50000,
      "EffectiveDate": "2025-01-20"
    }
  ]
}
```

---

## 4. UPDATE Order

### Endpoint
```
PATCH /services/data/v65.0/sobjects/Order/{order_id}
```

### Request Body
```json
{
  "Status": "Activated",
  "OrderReferenceNumber": "PO-2025-001-REV1",
  "Description": "Enterprise license renewal order - Updated pricing"
}
```

### Response (Success - 204 No Content)

**Important:** Orders cannot be edited once Status is "Activated". Only Draft orders can be updated.

---

## 5. ADD Order Products (OrderItem)

### Endpoint
```
POST /services/data/v65.0/sobjects/OrderItem
```

### Request Body
```json
{
  "OrderId": "8011234567890ABC",
  "Product2Id": "01t1234567890ABC",
  "PricebookEntryId": "01u1234567890ABC",
  "Quantity": 100,
  "UnitPrice": 500,
  "Description": "Enterprise License - 100 users"
}
```

### Response (Success - 201 Created)
```json
{
  "id": "8021234567890ABC",
  "success": true,
  "errors": []
}
```

### Required Fields for OrderItem
- **OrderId** (parent order)
- **PricebookEntryId** (price book entry for the product)
- **Quantity** (number of units)
- **UnitPrice** (price per unit)

---

## 6. DELETE Order

### Endpoint
```
DELETE /services/data/v65.0/sobjects/Order/{order_id}
```

### Response (Success - 204 No Content)

**Note:** Orders with Status "Activated" cannot be deleted. Only Draft orders can be deleted.

---

## 7. CREATE Order with Products (Composite API)

### Endpoint
```
POST /services/data/v65.0/commerce/sale/order
```

### Request Body (Full Order with Products)
```json
{
  "allOrNone": true,
  "records": [
    {
      "attributes": { "type": "Order", "referenceId": "ref1" },
      "AccountId": "0011234567890ABC",
      "EffectiveDate": "2025-01-20",
      "Status": "Draft",
      "Pricebook2Id": "01s1234567890ABC",
      "BillingStreet": "123 Main St",
      "BillingCity": "San Francisco",
      "BillingState": "CA",
      "BillingPostalCode": "94102",
      "BillingCountry": "USA",
      "OrderReferenceNumber": "PO-2025-001"
    }
  ],
  "orderProducts": [
    {
      "attributes": { "type": "OrderItem" },
      "Product2Id": "01t1234567890ABC",
      "PricebookEntryId": "01u1234567890ABC",
      "Quantity": 100,
      "UnitPrice": 500
    },
    {
      "attributes": { "type": "OrderItem" },
      "Product2Id": "01t9876543210XYZ",
      "PricebookEntryId": "01u9876543210XYZ",
      "Quantity": 50,
      "UnitPrice": 200
    }
  ]
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

# Create Order
def create_order(account_id, effective_date, pricebook_id, reference_number=None):
    url = f"{instance_url}/services/data/v65.0/sobjects/Order"
    
    payload = {
        "AccountId": account_id,
        "EffectiveDate": effective_date,  # Format: YYYY-MM-DD
        "Status": "Draft",
        "Pricebook2Id": pricebook_id
    }
    
    if reference_number:
        payload["OrderReferenceNumber"] = reference_number
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Add Product to Order
def add_order_product(order_id, product_id, pricebook_entry_id, quantity, unit_price):
    url = f"{instance_url}/services/data/v65.0/sobjects/OrderItem"
    
    payload = {
        "OrderId": order_id,
        "Product2Id": product_id,
        "PricebookEntryId": pricebook_entry_id,
        "Quantity": quantity,
        "UnitPrice": unit_price
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Activate Order
def activate_order(order_id):
    url = f"{instance_url}/services/data/v65.0/sobjects/Order/{order_id}"
    payload = {"Status": "Activated"}
    
    response = requests.patch(url, json=payload, headers=headers)
    return response.status_code == 204

# Get Orders for Account
def get_orders_for_account(account_id):
    query = f"SELECT Id, OrderNumber, Status, TotalAmount, EffectiveDate FROM Order WHERE AccountId = '{account_id}'"
    url = f"{instance_url}/services/data/v65.0/query"
    params = {"q": query}
    
    response = requests.get(url, params=params, headers=headers)
    return response.json()["records"]

# Usage
order = create_order(
    account_id="0011234567890ABC",
    effective_date="2025-01-20",
    pricebook_id="01s1234567890ABC",
    reference_number="PO-2025-001"
)
order_id = order["id"]
print(f"Created Order ID: {order_id}")

# Add products
add_order_product(
    order_id=order_id,
    product_id="01t1234567890ABC",
    pricebook_entry_id="01u1234567890ABC",
    quantity=100,
    unit_price=500
)

# Activate order
activate_order(order_id)
print("Order activated")
```

---

## Common Field Reference

| Field API Name | Type | Description | Required |
|----------------|------|-------------|----------|
| AccountId | Reference | Associated Account ID | Yes* |
| ContractId | Reference | Associated Contract ID | Yes* |
| EffectiveDate | Date | Date order becomes effective | Yes |
| Status | Picklist | Order status | Yes |
| Pricebook2Id | Reference | Price book ID | Yes** |
| OrderNumber | Auto Number | Auto-generated order number | Read-Only |
| TotalAmount | Currency | Total order amount | Read-Only |
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
| BillToContactId | Reference | Bill to contact ID | No |
| ShipToContactId | Reference | Ship to contact ID | No |
| OrderReferenceNumber | String(80) | Custom PO/reference number | No |
| Description | Textarea | Order description | No |
| CustomerAuthorized | Boolean | Whether customer authorized | No |
| CompanyAuthorized | Boolean | Whether company authorized | No |
| ActivatedDate | DateTime | Date order was activated | Read-Only |
| ActivatedById | Reference | User who activated order | Read-Only |

*Either AccountId OR ContractId required
**Can be disabled in some orgs

---

## Order Status Picklist Values

- **Draft** - Being created (editable)
- **Activated** - Confirmed and active (read-only)

**Important:** Once Status = "Activated", the Order becomes **read-only** and cannot be edited or deleted.

---

## cURL Examples

### Create Order
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Order" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "AccountId": "0011234567890ABC",
    "EffectiveDate": "2025-01-20",
    "Status": "Draft",
    "Pricebook2Id": "01s1234567890ABC",
    "OrderReferenceNumber": "PO-2025-001"
  }'
```

### Add Order Product
```bash
curl -X POST "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/OrderItem" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "OrderId": "8011234567890ABC",
    "Product2Id": "01t1234567890ABC",
    "PricebookEntryId": "01u1234567890ABC",
    "Quantity": 100,
    "UnitPrice": 500
  }'
```

### Activate Order
```bash
curl -X PATCH "https://yourinstance.my.salesforce.com/services/data/v65.0/sobjects/Order/8011234567890ABC" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type": "application/json" \
  -d '{
    "Status": "Activated"
  }'
```

---

## Best Practices

1. **Always create as Draft** - Status must be "Draft" initially
2. **Add all products before activating** - Can't edit after activation
3. **Use OrderReferenceNumber** - Store customer PO number
4. **Set billing/shipping addresses** - Required for invoicing
5. **Link to Account** - Always set AccountId
6. **Use Pricebook** - Ensures consistent pricing
7. **Validate before activating** - Orders become read-only
8. **Use Composite API** - Create order + products in one call
9. **Track activation** - ActivatedDate and ActivatedById are auto-set
10. **Link to Opportunity** - Use Opportunity.hasOpportunityLineItem

---

## Order Lifecycle

1. **Draft** - Create order, add products, set details
2. **Validate** - Check all required fields and products
3. **Activate** - Set Status = "Activated"
4. **Locked** - Order becomes read-only
5. **Fulfillment** - Process order (external system)

---

## Working with Products

### To add products to an order:

1. **Create Order** (Status = "Draft")
2. **Create OrderItems** (products) linked to Order
3. **Activate Order** (Status = "Activated")

### Required for each OrderItem:
- OrderId (parent order)
- Product2Id (product being ordered)
- PricebookEntryId (price book entry for that product)
- Quantity (number of units)
- UnitPrice (price per unit)

---

## Next Steps

- See [Account API Documentation](./02_account.md) to link orders to accounts
- See [Opportunity API Documentation](./04_opportunity.md) for pre-sale opportunities
- See [Product2 API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_basic_info.htm) for products
- See [Pricebook2 API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/resources_sobject_basic_info.htm) for price books
