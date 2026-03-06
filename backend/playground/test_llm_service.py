"""
Quick smoke test for LLMService — Bedrock (primary) + Groq (fallback).
Tests both structured output (agent-style) and plain text (memory/RAG style).
"""

import asyncio
import sys
import os
import time

# Fix imports
sys.path.insert(0, os.path.dirname(__file__) + "/..")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


# ── Minimal Pydantic model (mimics TriageState) ──

class TestCategory(str, Enum):
    ILLEGAL_EVICTION = "illegal_eviction"
    DOMESTIC_VIOLENCE = "domestic_violence"
    SENIOR_CITIZEN_NEGLECT = "senior_citizen_neglect"

class TestStructuredOutput(BaseModel):
    category: TestCategory = Field(description="The crisis category")
    summary: str = Field(description="A 1-sentence summary of the situation")
    urgency: int = Field(description="Urgency 1-5, where 5 is life-threatening")
    next_question: Optional[str] = Field(None, description="Follow-up question to ask")


# ── Tests ──

async def test_structured_output(llm):
    """Test 1: Structured output (what agents use)."""
    print("\n" + "="*60)
    print("TEST 1: Structured Output (Bedrock → Groq fallback)")
    print("="*60)

    messages = [
        {"role": "system", "content": "You are a crisis triage assistant for Karnataka, India. Classify the user's situation and respond with structured JSON."},
        {"role": "user", "content": "My landlord changed the locks while I was at work yesterday. All my belongings are inside. I have a rent agreement but he says I have to leave."}
    ]

    start = time.time()
    try:
        result = await llm.create_structured(
            response_model=TestStructuredOutput,
            messages=messages,
        )
        elapsed = time.time() - start
        print(f"  ✅ SUCCESS ({elapsed:.1f}s)")
        print(f"  Category:  {result.category.value}")
        print(f"  Summary:   {result.summary}")
        print(f"  Urgency:   {result.urgency}")
        print(f"  Next Q:    {result.next_question}")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ FAILED ({elapsed:.1f}s): {e}")
        return False


async def test_plain_completion(llm):
    """Test 2: Plain text completion (what memory summarization uses)."""
    print("\n" + "="*60)
    print("TEST 2: Plain Text Completion (Bedrock → Groq fallback)")
    print("="*60)

    messages = [
        {"role": "system", "content": "You are a conversation summarizer. Summarize the following exchange in 2-3 sentences."},
        {"role": "user", "content": """Summarize this conversation:
User: My father-in-law is threatening to throw me out of the house.
AI: I'm sorry to hear that. Are you currently in any physical danger?
User: No, but he cut off the electricity to my room yesterday.
AI: That sounds like economic abuse. Do you have any documentation of your residence there?
User: I have my Aadhaar card with this address and some utility bills."""}
    ]

    start = time.time()
    try:
        result = await llm.create_completion(messages=messages)
        elapsed = time.time() - start
        print(f"  ✅ SUCCESS ({elapsed:.1f}s)")
        print(f"  Summary: {result[:300]}")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ FAILED ({elapsed:.1f}s): {e}")
        return False


async def test_sync_structured(llm):
    """Test 3: Sync structured output (what RAG query parsing uses)."""
    print("\n" + "="*60)
    print("TEST 3: Sync Structured Output (RAG-style)")
    print("="*60)

    class SearchPlan(BaseModel):
        search_queries: List[str] = Field(description="3 search queries for vector database")

    messages = [
        {"role": "system", "content": "Generate 3 search queries for a legal knowledge base to answer the user's question. Return JSON."},
        {"role": "user", "content": "Can my landlord evict me without a court order in Karnataka?"}
    ]

    start = time.time()
    try:
        result = llm.create_structured_sync(
            response_model=SearchPlan,
            messages=messages,
        )
        elapsed = time.time() - start
        print(f"  ✅ SUCCESS ({elapsed:.1f}s)")
        for i, q in enumerate(result.search_queries, 1):
            print(f"  Query {i}: {q}")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ FAILED ({elapsed:.1f}s): {e}")
        return False


async def test_sync_completion(llm):
    """Test 4: Sync plain text (what RAG answer generation uses)."""
    print("\n" + "="*60)
    print("TEST 4: Sync Plain Text Completion (RAG answer-style)")
    print("="*60)

    messages = [
        {"role": "user", "content": """Based on the following legal context, answer the question.

Context:
Under the Karnataka Rent Act 1999, a landlord can only evict a tenant on grounds specified in Section 21, 
which include non-payment of rent, subletting without consent, nuisance, and bona fide personal need. 
Even for valid grounds, the landlord must file a petition before the Rent Tribunal.

Question: Can my landlord evict me without going to court?

Provide a clear, helpful answer."""}
    ]

    start = time.time()
    try:
        result = llm.create_completion_sync(messages=messages, temperature=0.25)
        elapsed = time.time() - start
        print(f"  ✅ SUCCESS ({elapsed:.1f}s)")
        print(f"  Answer: {result[:400]}")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ FAILED ({elapsed:.1f}s): {e}")
        return False


async def main():
    print("🚀 Sahayak LLM Service — Smoke Test")
    print("   Bedrock model: us.meta.llama3-2-90b-instruct-v1:0")
    print("   Groq fallback: llama-3.3-70b-versatile")

    from services.llm_service import LLMService
    llm = LLMService()

    results = []
    results.append(await test_structured_output(llm))
    results.append(await test_plain_completion(llm))
    results.append(await test_sync_structured(llm))
    results.append(await test_sync_completion(llm))

    print("\n" + "="*60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    print("="*60)

    if not all(results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
