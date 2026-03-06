#!/usr/bin/env python3
"""
RAG Knowledge Base — Before / After Comparison Test
=====================================================
Run BEFORE and AFTER ingesting the knowledge base to measure improvement.

Usage:
    python test_rag_comparison.py --phase before
    python test_rag_comparison.py --phase after
    python test_rag_comparison.py --compare
"""

import asyncio, json, sys, os, argparse
from datetime import datetime
from pathlib import Path
from textwrap import shorten

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.rag_service import RAGService

RESULTS_DIR = Path(__file__).parent / "rag_test_results"

# ─── Test queries covering all 3 tracks + cross-cutting ───

TEST_QUERIES = [
    # ── EVICTION ──
    {"id": "evict_01", "track": "eviction",
     "query": "My landlord is threatening to evict me without giving any notice in Bangalore. What are my legal rights under the Karnataka Rent Act?"},
    {"id": "evict_02", "track": "eviction",
     "query": "How much notice period is legally required before eviction in Karnataka? What section covers this?"},
    {"id": "evict_03", "track": "eviction",
     "query": "My landlord has illegally cut off water and electricity to force me to leave. Is this a criminal offence?"},
    {"id": "evict_04", "track": "eviction",
     "query": "What are the court fees for filing an injunction against illegal eviction in a Bangalore court?"},
    {"id": "evict_05", "track": "eviction",
     "query": "My landlord is refusing to return my security deposit after I vacated. What is the legal remedy?"},
    {"id": "evict_06", "track": "eviction",
     "query": "How do I get a temporary injunction to stop my landlord from throwing me out?"},

    # ── DOMESTIC VIOLENCE ──
    {"id": "dv_01", "track": "dv",
     "query": "My husband is beating me regularly. How do I file a domestic violence case in Bangalore?"},
    {"id": "dv_02", "track": "dv",
     "query": "What is a protection order under the DV Act and how quickly can I get one?"},
    {"id": "dv_03", "track": "dv",
     "query": "My husband violated the protection order and came to my house. What can I do? What is the penalty?"},
    {"id": "dv_04", "track": "dv",
     "query": "I need emergency shelter as a domestic violence victim in Bangalore. Where can I go?"},
    {"id": "dv_05", "track": "dv",
     "query": "Can I get maintenance money from my husband while the DV case is still going on?"},
    {"id": "dv_06", "track": "dv",
     "query": "What forms do I need to fill for filing a Domestic Incident Report? What is Form I?"},

    # ── SENIOR CITIZEN ──
    {"id": "senior_01", "track": "senior",
     "query": "My son is refusing to take care of me and wants to throw me out of my own house. What legal options do I have?"},
    {"id": "senior_02", "track": "senior",
     "query": "How do I file a maintenance application at the Senior Citizens Tribunal in Karnataka?"},
    {"id": "senior_03", "track": "senior",
     "query": "My son forced me to transfer my property to his name. Can the transfer be declared void?"},
    {"id": "senior_04", "track": "senior",
     "query": "What is the maximum maintenance amount a tribunal can order children to pay under the Senior Citizens Act?"},

    # ── CROSS-CUTTING ──
    {"id": "cross_01", "track": "cross",
     "query": "How do I file an FIR at the police station? What if the police refuse to register it?"},
    {"id": "cross_02", "track": "cross",
     "query": "What is the income limit for getting free legal aid in Karnataka?"},
    {"id": "cross_03", "track": "cross",
     "query": "Are WhatsApp messages and photos admissible as evidence in Indian courts?"},
    {"id": "cross_04", "track": "cross",
     "query": "How do I get a medico-legal certificate (MLC) for my injuries from a hospital?"},
    {"id": "cross_05", "track": "cross",
     "query": "Which court in Bangalore should I file my case in based on where I live?"},
    {"id": "cross_06", "track": "cross",
     "query": "What emergency helpline numbers are available for women, domestic violence, and elderly abuse?"},
]


def run_test(phase: str):
    """Run all test queries and save results."""
    print(f"\n{'=' * 60}")
    print(f"  RAG Test — Phase: {phase.upper()}")
    print(f"{'=' * 60}\n")

    rag = RAGService()
    count = rag.collection.count()
    print(f"  ChromaDB collection size: {count} chunks\n")

    results = []
    for i, test in enumerate(TEST_QUERIES):
        print(f"[{i + 1}/{len(TEST_QUERIES)}] {test['track'].upper():8s} | {test['query'][:65]}...")
        try:
            response = rag.search(test["query"])
            result = {
                "id": test["id"],
                "track": test["track"],
                "query": test["query"],
                "success": response.success,
                "answer": response.answer,
                "chunk_count": response.chunk_count,
                "search_queries": response.search_queries,
                "reasoning_questions": response.reasoning_questions,
                "error": response.error,
            }
            has_data = response.success and response.chunk_count > 0
            icon = "✅" if has_data else ("⚠️" if response.success else "❌")
            ans_preview = shorten(response.answer or "None", 90)
            print(f"  {icon} chunks={response.chunk_count:2d} | {ans_preview}\n")
        except Exception as e:
            result = {
                "id": test["id"],
                "track": test["track"],
                "query": test["query"],
                "success": False,
                "answer": None,
                "chunk_count": 0,
                "search_queries": [],
                "reasoning_questions": [],
                "error": str(e),
            }
            print(f"  ❌ Error: {e}\n")
        results.append(result)

    # ── Persist ──
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "phase": phase,
        "timestamp": datetime.now().isoformat(),
        "collection_size": count,
        "total_queries": len(TEST_QUERIES),
        "successful": sum(1 for r in results if r["success"]),
        "with_chunks": sum(1 for r in results if r.get("chunk_count", 0) > 0),
        "results": results,
    }
    filepath = RESULTS_DIR / f"rag_test_{phase}.json"
    filepath.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"\n{'=' * 60}")
    print(f"  Summary ({phase})")
    print(f"  Successful:  {output['successful']}/{output['total_queries']}")
    print(f"  With chunks: {output['with_chunks']}/{output['total_queries']}")
    print(f"  Saved to:    {filepath}")
    print(f"{'=' * 60}\n")


def compare_results():
    """Side-by-side comparison of before / after results."""
    before_path = RESULTS_DIR / "rag_test_before.json"
    after_path = RESULTS_DIR / "rag_test_after.json"
    if not before_path.exists():
        print("❌  No 'before' results. Run with  --phase before  first.")
        return
    if not after_path.exists():
        print("❌  No 'after' results. Run with  --phase after  first.")
        return

    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())

    print(f"\n{'=' * 72}")
    print(f"  RAG Before / After Comparison")
    print(f"{'=' * 72}")
    print(f"  BEFORE  {before['timestamp']}  |  collection: {before['collection_size']} chunks")
    print(f"  AFTER   {after['timestamp']}  |  collection: {after['collection_size']} chunks")
    delta_chunks = after["collection_size"] - before["collection_size"]
    print(f"  Δ chunks: +{delta_chunks}\n")

    before_map = {r["id"]: r for r in before["results"]}
    after_map = {r["id"]: r for r in after["results"]}

    improved = 0
    regressed = 0
    same = 0

    for tid in before_map:
        b = before_map[tid]
        a = after_map.get(tid, {})
        bc = b.get("chunk_count", 0)
        ac = a.get("chunk_count", 0)

        if ac > bc:
            tag = "📈 IMPROVED"
            improved += 1
        elif ac < bc:
            tag = "📉 REGRESSED"
            regressed += 1
        else:
            tag = "—  same"
            same += 1

        print(f"  [{b['track']:8s}] {tid:12s}  chunks {bc:2d} → {ac:2d}  {tag}")
        if ac > bc:
            print(f"    BEFORE: {shorten(b.get('answer') or 'NO ANSWER', 100)}")
            print(f"    AFTER : {shorten(a.get('answer') or 'NO ANSWER', 100)}")
            print()

    print(f"\n{'=' * 72}")
    print(f"  📊  Improvements : {improved}")
    print(f"      Regressions  : {regressed}")
    print(f"      No change    : {same}")
    print(f"{'=' * 72}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG Before/After Test")
    parser.add_argument("--phase", choices=["before", "after"])
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    if args.compare:
        compare_results()
    elif args.phase:
        run_test(args.phase)
    else:
        parser.print_help()
