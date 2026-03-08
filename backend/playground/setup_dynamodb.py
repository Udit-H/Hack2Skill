#!/usr/bin/env python3
"""
DynamoDB Table Setup Script
============================
Creates ALL Sahayak DynamoDB tables:
  1. sahayak-chat-messages   – conversation history
  2. sahayak-rag-cache       – RAG retrieval cache (saves Cohere/ChromaDB costs)
  3. sahayak-session-summaries – L2 episodic memory summaries

Run this once during initial deployment.

Usage:
    python setup_dynamodb.py
"""

import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3
from botocore.exceptions import ClientError
from config.config import Settings
from services.chat_storage_service import ChatStorageService


def _get_dynamodb_client():
    settings = Settings()
    return boto3.client(
        "dynamodb",
        region_name=settings.llm.aws_region,
        aws_access_key_id=settings.llm.aws_access_key_id,
        aws_secret_access_key=settings.llm.aws_secret_access_key,
    )


def _create_simple_table(client, table_name: str, pk_name: str, pk_type: str = "S"):
    """Create a simple single-partition-key table if it doesn't already exist."""
    try:
        client.describe_table(TableName=table_name)
        print(f"   ✅ {table_name} already exists")
        return
    except client.exceptions.ResourceNotFoundException:
        pass

    print(f"   ⏳ Creating {table_name} ...")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": pk_name, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": pk_name, "AttributeType": pk_type}],
        BillingMode="PAY_PER_REQUEST",
    )
    # Wait until table is active
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=table_name, WaiterConfig={"Delay": 2, "MaxAttempts": 30})
    print(f"   ✅ {table_name} created")


def _enable_ttl(client, table_name: str, ttl_attr: str):
    """Enable TTL on a table (idempotent)."""
    try:
        resp = client.describe_time_to_live(TableName=table_name)
        status = resp.get("TimeToLiveDescription", {}).get("TimeToLiveStatus", "")
        if status in ("ENABLED", "ENABLING"):
            return
        client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={"Enabled": True, "AttributeName": ttl_attr},
        )
        print(f"   🕐 TTL enabled on {table_name}.{ttl_attr}")
    except Exception as e:
        print(f"   ⚠️  TTL setup skipped for {table_name}: {e}")


def main():
    region = os.getenv("AWS_REGION", "us-east-1")
    print(f"🚀 Setting up ALL Sahayak DynamoDB tables (region: {region})\n")

    client = _get_dynamodb_client()

    # 1. Chat messages table (composite key: session_id + timestamp)
    chat_table = os.getenv("DYNAMODB_CHAT_TABLE", "sahayak-chat-messages")
    print(f"[1/3] Chat messages: {chat_table}")
    try:
        storage = ChatStorageService()
        storage.create_table_if_not_exists()
        print(f"   ✅ {chat_table} ready")
    except Exception as e:
        print(f"   ❌ {chat_table} failed: {e}")

    print()

    # 2. RAG retrieval cache (PK: query_hash, TTL on expires_at)
    cache_table = os.getenv("RAG_CACHE_TABLE", "sahayak-rag-cache")
    print(f"[2/3] RAG cache: {cache_table}")
    _create_simple_table(client, cache_table, "query_hash")
    _enable_ttl(client, cache_table, "expires_at")

    print()

    # 3. Session summaries (PK: session_id)
    summary_table = os.getenv("DYNAMODB_SUMMARY_TABLE", "sahayak-session-summaries")
    print(f"[3/3] Session summaries: {summary_table}")
    _create_simple_table(client, summary_table, "session_id")

    print("\n🎉 All tables ready!")


if __name__ == "__main__":
    main()
