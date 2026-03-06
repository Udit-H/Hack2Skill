#!/usr/bin/env python3
"""
DynamoDB Chat Storage Test
===========================
Tests the chat storage service with sample messages.

Usage:
    python test_dynamodb_storage.py
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.chat_storage_service import ChatStorageService


async def test_chat_storage():
    """Test all CRUD operations on DynamoDB chat storage."""
    
    print("🧪 Testing DynamoDB Chat Storage Service\n")
    print("=" * 60)
    
    storage = ChatStorageService()
    test_session_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Test 1: Save user message
    print("\n1️⃣  Saving user message...")
    success = await storage.save_message(
        session_id=test_session_id,
        role="user",
        content="I need help with an eviction notice",
        agent_type="triage",
    )
    assert success, "Failed to save user message"
    print("   ✅ User message saved")
    
    # Test 2: Save assistant message with metadata
    print("\n2️⃣  Saving assistant message with metadata...")
    success = await storage.save_message(
        session_id=test_session_id,
        role="assistant",
        content="I can help you with that. Let me gather some details.",
        agent_type="triage",
        metadata={
            "progress_status": "collecting information",
            "is_loading": False,
        }
    )
    assert success, "Failed to save assistant message"
    print("   ✅ Assistant message saved")
    
    # Test 3: Save multiple messages
    print("\n3️⃣  Saving multiple messages in conversation...")
    for i in range(3):
        await storage.save_message(
            session_id=test_session_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Test message {i + 1}",
            agent_type="legal",
        )
    print("   ✅ Multiple messages saved")
    
    # Test 4: Retrieve chat history
    print("\n4️⃣  Retrieving chat history...")
    messages = await storage.get_session_history(test_session_id, limit=10)
    print(f"   ✅ Retrieved {len(messages)} messages")
    
    # Verify message order and content
    assert len(messages) >= 5, f"Expected at least 5 messages, got {len(messages)}"
    assert messages[0]['role'] == 'user', "First message should be from user"
    assert messages[0]['content'] == "I need help with an eviction notice"
    print(f"   ✅ Messages in correct order")
    
    # Display messages
    print("\n   📋 Chat History:")
    for i, msg in enumerate(messages, 1):
        timestamp = msg['timestamp']
        role = msg['role'].upper()
        content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
        agent = msg.get('agent_type', 'N/A')
        print(f"      {i}. [{timestamp}] {role} ({agent}): {content}")
        if msg.get('metadata'):
            print(f"         Metadata: {msg['metadata']}")
    
    # Test 5: Delete session history
    print("\n5️⃣  Deleting session history (cleanup)...")
    success = await storage.delete_session_history(test_session_id)
    assert success, "Failed to delete session"
    print("   ✅ Session deleted")
    
    # Verify deletion
    messages = await storage.get_session_history(test_session_id)
    assert len(messages) == 0, f"Expected 0 messages after deletion, got {len(messages)}"
    print("   ✅ Verified deletion: 0 messages remaining")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! DynamoDB chat storage is working correctly.")
    print("\n💡 You can now use the chat endpoint and messages will be persisted.")


if __name__ == "__main__":
    try:
        asyncio.run(test_chat_storage())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
