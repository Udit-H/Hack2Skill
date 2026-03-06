# DynamoDB Chat Storage Setup

## Overview

All chat messages between users and Sahayak are now persisted in AWS DynamoDB for:
- **Audit trails**: Track all conversations for compliance
- **Analytics**: Aggregate usage patterns, agent performance
- **Session recovery**: Restore conversations if backend restarts
- **Privacy compliance**: Permanent deletion via panic wipe

## Table Schema

**Table Name**: `sahayak-chat-messages` (configurable via `DYNAMODB_CHAT_TABLE` env var)

| Attribute    | Type   | Key Type | Description                                    |
|--------------|--------|----------|------------------------------------------------|
| session_id   | String | HASH     | Partition key - unique session identifier      |
| timestamp    | String | RANGE    | Sort key - ISO 8601 timestamp                  |
| role         | String | —        | 'user' or 'assistant'                          |
| content      | String | —        | Message text                                   |
| agent_type   | String | —        | Active agent (triage, legal, shelter, etc.)    |
| metadata     | Map    | —        | Optional: progress_status, errors, downloads   |

**Billing Mode**: Pay-per-request (no capacity planning needed)

## Setup Instructions

### 1. Prerequisites

- AWS account with DynamoDB access
- IAM credentials configured in `.env`:
  ```env
  AWS_REGION=us-east-1
  AWS_ACCESS_KEY_ID=your_access_key
  AWS_SECRET_ACCESS_KEY=your_secret_key
  DYNAMODB_CHAT_TABLE=sahayak-chat-messages  # Optional: defaults to this
  ```

### 2. IAM Policy

Attach this policy to your backend app's IAM user/role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBChatStorage",
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/sahayak-chat-messages",
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/sahayak-chat-messages/*"
      ]
    }
  ]
}
```

### 3. Create Table

Run the setup script (only once during deployment):

```bash
cd backend/playground
python setup_dynamodb.py
```

Or with a custom table name:

```bash
python setup_dynamodb.py --table-name my-custom-chat-table
```

### 4. Verify Setup

```bash
# Check table exists
aws dynamodb describe-table --table-name sahayak-chat-messages

# Test a chat message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-123", "message": "Hello"}'

# Retrieve chat history
curl http://localhost:8000/api/chat-history/test-123
```

## API Endpoints

### Save Message (Automatic)
Messages are automatically saved when you call `/api/chat`. No manual action required.

### Retrieve History
```http
GET /api/chat-history/{session_id}?limit=50
```

**Response**:
```json
{
  "success": true,
  "session_id": "s-abc123",
  "message_count": 12,
  "messages": [
    {
      "session_id": "s-abc123",
      "timestamp": "2026-03-06T10:30:00.123Z",
      "role": "user",
      "content": "I need help with eviction",
      "agent_type": "triage"
    },
    {
      "session_id": "s-abc123",
      "timestamp": "2026-03-06T10:30:02.456Z",
      "role": "assistant",
      "content": "I understand. Let me gather some details...",
      "agent_type": "triage",
      "metadata": {
        "progress_status": "collecting information"
      }
    }
  ]
}
```

### Delete History (Panic Wipe)
```http
POST /api/panic
Content-Type: application/json

{"session_id": "s-abc123"}
```

Permanently deletes all DynamoDB records + Redis memory for the session.

## Cost Estimation

**DynamoDB Pricing** (Pay-per-request, us-east-1):
- **Write**: $1.25 per million writes
- **Read**: $0.25 per million reads
- **Storage**: $0.25 per GB-month

**Example**: 10,000 sessions/month × 20 messages each = 200K writes = **$0.25/month**

## Monitoring

### CloudWatch Metrics
- `ConsumedWriteCapacityUnits`
- `ConsumedReadCapacityUnits`
- `UserErrors` (throttling, validation failures)

### Application Logs
```python
# Success: 
💾 Saved user message for session s-abc123

# Failure:
❌ DynamoDB write error: ResourceNotFoundException
```

## Best Practices

1. **Enable Point-in-Time Recovery** for backup/restore:
   ```bash
   aws dynamodb update-continuous-backups \
     --table-name sahayak-chat-messages \
     --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
   ```

2. **Set TTL** for auto-deletion after 90 days (GDPR compliance):
   - Add `ttl` attribute (Unix timestamp) to items
   - Enable TTL on the table

3. **Monitor costs**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name ConsumedWriteCapacityUnits \
     --dimensions Name=TableName,Value=sahayak-chat-messages \
     --statistics Sum \
     --start-time 2026-03-01T00:00:00Z \
     --end-time 2026-03-07T00:00:00Z \
     --period 86400
   ```

4. **Backup strategy**:
   - On-demand backups before major releases
   - Export to S3 for long-term archival/analytics

## Troubleshooting

### Table not found
```
❌ DynamoDB read error: ResourceNotFoundException
```
**Fix**: Run `python setup_dynamodb.py`

### Access denied
```
❌ DynamoDB write error: AccessDeniedException
```
**Fix**: Verify IAM policy and credentials in `.env`

### Throttling
```
❌ DynamoDB write error: ProvisionedThroughputExceededException
```
**Fix**: Should not happen with on-demand billing. Check for runaway loops.

## Migration Path

If migrating from in-memory chat history:

1. Deploy this change (messages start saving to DynamoDB)
2. Old sessions continue working (history still in `SessionState.chat_history`)
3. New sessions load from DynamoDB on next request (optional feature)
4. No data loss, no downtime

## Future Enhancements

- [ ] **Session recovery**: Auto-load history from DynamoDB on session creation
- [ ] **Full-text search**: Add GSI on content for keyword search
- [ ] **Analytics pipeline**: S3 export → Athena/QuickSight for insights
- [ ] **Multi-region**: DynamoDB Global Tables for low-latency worldwide
