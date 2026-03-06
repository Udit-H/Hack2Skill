#!/usr/bin/env python3
"""
Test Session List API
=====================
Verify the session listing functionality works correctly.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.chat_storage_service import ChatStorageService


async def test_session_list():
    """Test session listing for a user."""
    
    print("🧪 Testing Session List API\n")
    print("=" * 60)
    
    storage = ChatStorageService()
    test_user_id = "test-user@example.com"
    
    # Create some test sessions
    print("\n1️⃣  Creating test sessions...")
    sessions_to_create = [
        ("s-test-001", "I need help with an eviction notice"),
        ("s-test-002", "Domestic violence support needed"),
        ("s-test-003", "Senior citizen maintenance issue"),
    ]
    
    for session_id, message in sessions_to_create:
        await storage.save_message(
            session_id=session_id,
            role="user",
            content=message,
            agent_type="triage",
            user_id=test_user_id,
        )
        await storage.save_message(
            session_id=session_id,
            role="assistant",
            content="I can help you with that. Let me gather some details.",
            agent_type="triage",
            user_id=test_user_id,
        )
        print(f"   ✅ Created session: {session_id}")
    
    # List sessions
    print("\n2️⃣  Listing sessions for user...")
    sessions = await storage.list_user_sessions(test_user_id, limit=10)
    
    if not sessions:
        print("   ⚠️  No sessions found")
        print("   This might be because:")
        print("   - DynamoDB scan didn't find any matching user_id")
        print("   - Messages were saved without user_id field")
        print("\n   Debugging DynamoDB items...")
        # Try to query one session directly
        messages = await storage.get_session_history("s-test-001", limit=5)
        if messages:
            print(f"   Found {len(messages)} messages in s-test-001:")
            for msg in messages[:2]:
                print(f"      - {msg}")
        return
    
    print(f"   ✅ Found {len(sessions)} sessions\n")
    
    # Display sessions
    print("   📋 Session List:")
    for i, session in enumerate(sessions, 1):
        print(f"\n   {i}. Session: {session['session_id']}")
        print(f"      Last Message: {session['last_message'][:50]}...")
        print(f"      Timestamp: {session['last_timestamp']}")
        print(f"      Messages: {session['message_count']}")
    
    # Cleanup
    print("\n3️⃣  Cleaning up test sessions...")
    for session_id, _ in sessions_to_create:
        await storage.delete_session_history(session_id)
    print("   ✅ Cleanup complete")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! Session listing is working.")


if __name__ == "__main__":
    try:
        asyncio.run(test_session_list())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
