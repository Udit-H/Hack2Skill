#!/usr/bin/env python3
"""
Knowledge Base Ingestion Script
================================
Reads all curated markdown files from backend/knowledge_base/
and ingests them into ChromaDB via RAGService.ingest_text().

Usage:
    python ingest_knowledge_base.py                # ingest all
    python ingest_knowledge_base.py --dry-run      # preview only
    python ingest_knowledge_base.py --file bare_acts/01_pwdva_2005.md
    python ingest_knowledge_base.py --clear        # wipe collection first
"""

import asyncio, sys, os, argparse
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.rag_service import RAGService

KB_DIR = Path(__file__).parent.parent / "knowledge_base"


async def ingest_all(dry_run: bool = False, specific_file: str = None, clear: bool = False):
    rag = RAGService()

    if clear:
        existing = rag.collection.count()
        if existing > 0:
            print(f"⚠️  Clearing {existing} existing chunks from collection...")
            # Get all IDs and delete
            all_ids = rag.collection.get()["ids"]
            if all_ids:
                rag.collection.delete(ids=all_ids)
            print(f"   Cleared. Collection now: {rag.collection.count()} chunks\n")

    # Discover documents
    if specific_file:
        md_files = [KB_DIR / specific_file]
        if not md_files[0].exists():
            print(f"❌ File not found: {md_files[0]}")
            return
    else:
        md_files = sorted(KB_DIR.rglob("*.md"))
        md_files = [f for f in md_files if f.name != "README.md"]

    print(f"\n{'=' * 60}")
    print(f"  Knowledge Base Ingestion")
    print(f"  Documents found : {len(md_files)}")
    print(f"  Collection now  : {rag.collection.count()} chunks")
    print(f"  Mode            : {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'=' * 60}\n")

    total_chunks = 0
    successes = 0
    failures = 0

    for i, filepath in enumerate(md_files):
        relative = filepath.relative_to(KB_DIR)
        content = filepath.read_text(encoding="utf-8")

        # Extract source from first markdown heading
        source = filepath.stem.replace("_", " ").title()
        for line in content.split("\n"):
            if line.startswith("# "):
                source = line[2:].strip()
                break

        # Category from parent directory
        doc_type = filepath.parent.name if filepath.parent != KB_DIR else "general"

        print(f"[{i + 1}/{len(md_files)}] {relative}")
        print(f"  Source : {source}")
        print(f"  Type   : {doc_type}  |  Size: {len(content):,} bytes")

        if dry_run:
            print(f"  [DRY RUN] skipped\n")
            continue

        result = await rag.ingest_text(content, source=source, doc_type=doc_type)

        if result["success"]:
            n = result["chunks_stored"]
            total_chunks += n
            successes += 1
            print(f"  ✅ {n} chunks ingested\n")
        else:
            failures += 1
            print(f"  ❌ {result.get('error', 'unknown')}\n")

    print(f"\n{'=' * 60}")
    print(f"  Ingestion Complete!")
    print(f"  Documents processed : {len(md_files)}")
    print(f"  Successes           : {successes}")
    print(f"  Failures            : {failures}")
    print(f"  Total new chunks    : {total_chunks}")
    print(f"  Collection total    : {rag.collection.count()} chunks")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Ingest knowledge base into ChromaDB")
    p.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    p.add_argument("--file", type=str, help="Ingest a single file (relative to knowledge_base/)")
    p.add_argument("--clear", action="store_true", help="Clear collection before ingesting")
    args = p.parse_args()
    asyncio.run(ingest_all(dry_run=args.dry_run, specific_file=args.file, clear=args.clear))
