# Email Sorting Plans

This directory contains email sorting plans for each account. Plans define rules for automatically organizing emails into folders.

## File Structure

Each account has its own JSON file named by account ID:

```
sorting-plans/
├── README.md
├── {accountId-1}.json
├── {accountId-2}.json
└── ...
```

## Plan Schema

```typescript
interface SortingPlan {
  version: "1.0";
  accountId: string;
  accountName: string;
  createdAt: string;           // ISO 8601
  updatedAt: string;           // ISO 8601
  enabled: boolean;
  folderStructure?: FolderDefinition[];
  rules: SortingRule[];
}
```

## Conditions

Rules support complex conditions with AND/OR/NOT logic:

### Field Condition
```json
{
  "type": "field",
  "field": "from",
  "operator": "regex",
  "value": "@(gmail|yahoo)\\.com$",
  "caseSensitive": false
}
```

### AND Condition
```json
{
  "type": "and",
  "conditions": [
    { "type": "field", "field": "from", "operator": "contains", "value": "@bank.com" },
    { "type": "field", "field": "subject", "operator": "contains", "value": "statement" }
  ]
}
```

### OR Condition
```json
{
  "type": "or",
  "conditions": [
    { "type": "field", "field": "from", "operator": "contains", "value": "@sberbank.ru" },
    { "type": "field", "field": "from", "operator": "contains", "value": "@tinkoff.ru" }
  ]
}
```

### NOT Condition
```json
{
  "type": "not",
  "condition": {
    "type": "field",
    "field": "subject",
    "operator": "contains",
    "value": "spam"
  }
}
```

## Available Fields

| Field | Description |
|-------|-------------|
| `from` | Sender email address |
| `to` | Recipient email addresses |
| `subject` | Email subject |
| `flags` | Email flags (e.g., \Seen, \Flagged) |
| `date` | Email date (timestamp) |

## Available Operators

| Operator | Description | Value Type |
|----------|-------------|------------|
| `contains` | String contains | string |
| `equals` | Exact match | string |
| `startsWith` | String starts with | string |
| `endsWith` | String ends with | string |
| `regex` | Regular expression match | string |
| `gt` | Greater than | number |
| `lt` | Less than | number |
| `between` | Between two values | [number, number] |

## Available Actions

| Action | Description | Requires |
|--------|-------------|----------|
| `move` | Move email to folder | targetFolder |
| `copy` | Copy email to folder | targetFolder |
| `markRead` | Mark email as read | - |
| `markUnread` | Mark email as unread | - |
| `delete` | Delete email | - |

## Example Plan

```json
{
  "version": "1.0",
  "accountId": "abc-123",
  "accountName": "my-gmail",
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-15T10:00:00Z",
  "enabled": true,
  "folderStructure": [
    { "path": "INBOX/Finance/Banking", "autoCreate": true },
    { "path": "INBOX/Tech", "autoCreate": true },
    { "path": "INBOX/Marketing", "autoCreate": true }
  ],
  "rules": [
    {
      "id": "rule-001",
      "name": "Banking emails",
      "enabled": true,
      "priority": 10,
      "conditions": {
        "type": "field",
        "field": "from",
        "operator": "regex",
        "value": "@(sberbank|tinkoff|vtb)\\.ru$"
      },
      "action": {
        "type": "move",
        "targetFolder": "INBOX/Finance/Banking"
      },
      "stopProcessing": true
    },
    {
      "id": "rule-002",
      "name": "Tech services",
      "enabled": true,
      "priority": 20,
      "conditions": {
        "type": "or",
        "conditions": [
          { "type": "field", "field": "from", "operator": "contains", "value": "@github.com" },
          { "type": "field", "field": "from", "operator": "contains", "value": "@aws.amazon.com" },
          { "type": "field", "field": "from", "operator": "contains", "value": "@google.com" }
        ]
      },
      "action": {
        "type": "move",
        "targetFolder": "INBOX/Tech"
      },
      "stopProcessing": false
    },
    {
      "id": "rule-003",
      "name": "Marketing/Newsletters",
      "enabled": true,
      "priority": 100,
      "conditions": {
        "type": "or",
        "conditions": [
          { "type": "field", "field": "from", "operator": "contains", "value": "noreply" },
          { "type": "field", "field": "from", "operator": "contains", "value": "newsletter" },
          { "type": "field", "field": "subject", "operator": "regex", "value": "(unsubscribe|отписаться)" }
        ]
      },
      "action": {
        "type": "move",
        "targetFolder": "INBOX/Marketing"
      },
      "stopProcessing": true
    }
  ]
}
```

## MCP Tools

### Plan Management
- `imap_get_sorting_plan` - Get plan for account
- `imap_save_sorting_plan` - Save/update plan
- `imap_delete_sorting_plan` - Delete plan
- `imap_list_sorting_plans` - List all plans

### Rule Management
- `imap_add_sorting_rule` - Add rule to plan
- `imap_update_sorting_rule` - Update rule
- `imap_delete_sorting_rule` - Delete rule
- `imap_reorder_sorting_rules` - Change rule priorities

### Execution
- `imap_apply_sorting_rules` - Apply rules to emails
- `imap_test_sorting_rule` - Test rule without applying

### Utilities
- `imap_create_folders_from_plan` - Create defined folders
- `imap_validate_sorting_plan` - Validate plan structure
- `imap_set_sorting_plans_directory` - Set storage directory
- `imap_get_sorting_plans_directory` - Get storage directory

## Usage Example

```bash
# 1. Create a plan
imap_save_sorting_plan(accountId="abc-123", rules=[...])

# 2. Create folders
imap_create_folders_from_plan(accountId="abc-123")

# 3. Test rules (dry run)
imap_apply_sorting_rules(accountId="abc-123", dryRun=true, limit=50)

# 4. Apply rules
imap_apply_sorting_rules(accountId="abc-123", onlyUnread=true)

# Daily sorting (only new emails)
imap_apply_sorting_rules(accountId="abc-123", onlyUnread=true, sinceDate="2025-01-15")
```
