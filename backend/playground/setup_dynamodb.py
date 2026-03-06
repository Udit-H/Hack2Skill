#!/usr/bin/env python3
"""
DynamoDB Table Setup Script
============================
Creates the Sahayak chat messages table in DynamoDB.
Run this once during initial deployment.

Usage:
    python setup_dynamodb.py
    python setup_dynamodb.py --table-name custom-table-name
"""

import sys
import os
import argparse

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.chat_storage_service import ChatStorageService


def main():
    parser = argparse.ArgumentParser(description="Create DynamoDB chat storage table")
    parser.add_argument(
        "--table-name",
        type=str,
        help="Custom table name (defaults to DYNAMODB_CHAT_TABLE env var or 'sahayak-chat-messages')",
    )
    args = parser.parse_args()
    
    # Override table name if provided
    if args.table_name:
        os.environ["DYNAMODB_CHAT_TABLE"] = args.table_name
    
    print("🚀 Setting up DynamoDB chat storage...")
    print(f"   Region: {os.getenv('AWS_REGION', 'us-east-1')}")
    print(f"   Table: {os.getenv('DYNAMODB_CHAT_TABLE', 'sahayak-chat-messages')}")
    print()
    
    try:
        storage = ChatStorageService()
        storage.create_table_if_not_exists()
        print("\n✅ Setup complete! Chat messages will be stored in DynamoDB.")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
