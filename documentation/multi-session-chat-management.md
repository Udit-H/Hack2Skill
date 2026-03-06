# Multi-Session Chat Management

## Overview

Users can now view all their previous conversations, switch between sessions, and create new chats without losing history. All conversations are persisted in DynamoDB and can be resumed at any time.

## Features

- **Session List**: View all previous chat sessions with message previews
- **Resume Conversations**: Click any session to continue where you left off
- **New Chat**: Start a fresh conversation while preserving old ones
- **User Identity Tracking**: Sessions are linked to authenticated users (email/phone)
- **Real-time Updates**: Chat history loads instantly when switching sessions

## Architecture

### Backend Changes

**1. DynamoDB Schema Enhancement**
- Added `user_id` field to track session ownership
- `list_user_sessions()` method to retrieve all sessions for a user
- Session filtering by user identity

**2. New API Endpoints**

```
POST /api/sessions/list
Body: { "user_id": "user@example.com" }
Response: { "sessions": [...], "session_count": 5 }

POST /api/sessions/load
Body: { "session_id": "s-abc123", "user_id": "user@example.com" }
Response: { "messages": [...], "agent_info": {...} }

POST /api/session (enhanced)
Body: { "user_id": "user@example.com" }  # Optional
```

**3. Updated Chat Endpoint**
- Now accepts `user_id` in ChatRequest
- Automatically links messages to user identity
- Persists user_id in DynamoDB for filtering

### Frontend Changes

**1. SessionList Component** ([src/components/SessionList.jsx](../frontend/src/components/SessionList.jsx))
- Modal overlay with session list
- Shows message preview, timestamp, message count
- Active session highlighting
- "New Chat" button

**2. useChat Hook Enhancement** ([src/hooks/useChat.js](../frontend/src/hooks/useChat.js))
- `loadExistingSession(sessionId)`: Load chat history
- `createNewSession()`: Start fresh conversation
- `userId`: Extracted from authenticated user
- Auto-passes userId to all API calls

**3. ChatApp Integration** ([src/components/ChatApp.jsx](../frontend/src/components/ChatApp.jsx))
- SessionList button in header
- Handlers for session switching and new chat creation

## User Flow

```
User lands on chat page
    ↓
Click "💬 Chats (3)" button
    ↓
Modal shows list of previous sessions
    - "Help with eviction notice" (2h ago, 15 messages)
    - "Domestic violence support" (1d ago, 23 messages)
    - "Senior citizen maintenance" (3d ago, 8 messages)
    ↓
User clicks a session
    ↓
Chat history loads from DynamoDB
Agent state restores to last position
User continues conversation
    ↓
OR click "➕ New Chat"
    ↓
Fresh session created
Old session preserved
```

## UI Design

### Session List Modal

**Features:**
- Dark overlay with backdrop blur
- Centered panel (500px max width)
- Scrollable session list
- Each session shows:
  - First 100 chars of last message
  - Relative timestamp (2h ago, 1d ago)
  - Message count
  - Active session indicator

**Styling:**
- Teal accent colors matching app theme
- Smooth animations (slide-up, fade-in)
- Hover effects on session items
- Mobile-responsive (90% width on small screens)

### Session Button

**Location:** Chat header, between agent avatar and language selector

**States:**
- Default: `💬 Chats (0)`
- With sessions: `💬 Chats (5)`
- Hover: Glow effect

## Technical Implementation

### Session Data Flow

```typescript
// 1. List sessions for user
POST /api/sessions/list { user_id: "user@example.com" }
→ DynamoDB scan/query by user_id
→ Group by session_id, get last message
→ Return sorted list (most recent first)

// 2. Load selected session
POST /api/sessions/load { session_id: "s-abc", user_id: "user@example.com" }
→ Query DynamoDB for all messages (partition key: session_id)
→ Sort by timestamp (ascending)
→ Load session state from Redis/memory
→ Return messages + agent_info

// 3. Continue conversation
POST /api/chat { session_id: "s-abc", message: "...", user_id: "..." }
→ Process through orchestrator
→ Save to DynamoDB with user_id
→ Update Redis memory
```

### Performance Considerations

**DynamoDB Optimization:**
- Current implementation uses `scan()` with FilterExpression (MVP approach)
- **Production optimization**: Add Global Secondary Index (GSI)
  - Partition key: `user_id`
  - Sort key: `timestamp`
  - Enables efficient `query()` instead of `scan()`

**Cost Impact:**
- Additional writes: ~2 per message (user + assistant)
- Additional reads: 1 query per session switch (~20 sessions listed)
- Estimated cost: +$0.10/month for 1000 users

**Caching Strategy:**
- Session list cached in React state
- Only refreshes when modal opens
- No polling (user-triggered refresh)

## Testing

### Backend Tests

```bash
# Test session listing
curl -X POST http://localhost:8000/api/sessions/list \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test@example.com"}'

# Test session loading
curl -X POST http://localhost:8000/api/sessions/load \
  -H "Content-Type: application/json" \
  -d '{"session_id": "s-abc123", "user_id": "test@example.com"}'

# Test chat with user_id
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "s-abc123",
    "message": "Hello",
    "user_id": "test@example.com"
  }'
```

### Frontend Testing

1. **Create Multiple Sessions**
   - Start chat, send 2-3 messages
   - Click "💬 Chats" → "➕ New Chat"
   - Send different messages
   - Repeat 3-4 times

2. **Verify Session List**
   - Click "💬 Chats"
   - Should see all sessions with previews
   - Timestamps should be relative (2m ago, 1h ago)
   - Current session should be highlighted

3. **Test Session Switching**
   - Click another session
   - Chat window clears
   - History loads (may take 1-2 seconds)
   - Can continue conversation

4. **Test New Chat**
   - Click "➕ New Chat"
   - Fresh empty chat
   - Old session still in list

## Known Limitations

1. **Session listing uses scan()**
   - Works for MVP but inefficient for 1000+ users
   - Add GSI before production (see setup below)

2. **No search/filter**
   - Users must scroll through session list
   - Future: Add search box for keywords

3. **No session deletion**
   - Only panic wipe deletes all sessions
   - Future: Add per-session delete button

4. **No session titles**
   - Uses first message as preview
   - Future: Generate smart titles with LLM

## Production Setup

### 1. Add DynamoDB GSI

```bash
aws dynamodb update-table \
  --table-name sahayak-chat-messages \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --global-secondary-index-updates '[
    {
      "Create": {
        "IndexName": "user-timestamp-index",
        "KeySchema": [
          {"AttributeName": "user_id", "KeyType": "HASH"},
          {"AttributeName": "timestamp", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"},
        "ProvisionedThroughput": {
          "ReadCapacityUnits": 5,
          "WriteCapacityUnits": 5
        }
      }
    }
  ]'
```

### 2. Update IAM Policy

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:Query",
    "dynamodb:Scan"
  ],
  "Resource": [
    "arn:aws:dynamodb:us-east-1:*:table/sahayak-chat-messages",
    "arn:aws:dynamodb:us-east-1:*:table/sahayak-chat-messages/index/user-timestamp-index"
  ]
}
```

### 3. Update Backend Code

```python
# In chat_storage_service.py, replace scan() with:
response = self.table.query(
    IndexName='user-timestamp-index',
    KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id),
    ScanIndexForward=False,  # Latest first
    Limit=limit,
)
```

## Future Enhancements

- [ ] **Session Titles**: Auto-generate from first user message
- [ ] **Session Search**: Filter by keywords, date range
- [ ] **Session Deletion**: Per-session delete (not just panic wipe)
- [ ] **Session Export**: Download as PDF/JSON
- [ ] **Session Sharing**: Share read-only link with lawyer/advocate
- [ ] **Session Analytics**: Show conversation stats (duration, agent switches)
- [ ] **Session Tags**: User-defined labels (eviction, DV, senior care)
- [ ] **Session Folders**: Organize related conversations
- [ ] **Infinite Scroll**: Lazy-load sessions as user scrolls

## Accessibility

- **Keyboard Navigation**: Tab through session list, Enter to select
- **Screen Readers**: Proper ARIA labels on buttons and modals
- **Color Contrast**: All text meets WCAG AA standards
- **Focus Management**: Modal traps focus, ESC key closes

## Security Considerations

- **User Isolation**: Sessions filtered by authenticated user_id
- **Authorization**: Backend validates user owns session before loading
- **Panic Wipe**: Still deletes all sessions for user
- **No Cross-User Access**: DynamoDB queries scoped to user_id

## Rollback Plan

If issues arise:

1. **Disable feature flag** (add to config):
   ```javascript
   const FEATURE_SESSION_MANAGEMENT = false;
   ```

2. **Hide SessionList component**:
   ```jsx
   {FEATURE_SESSION_MANAGEMENT && <SessionList ... />}
   ```

3. **Backend remains backwards compatible**:
   - Old clients work without `user_id` in requests
   - New fields optional in DynamoDB

No data loss, graceful degradation.
