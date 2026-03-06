import asyncio
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.rag_service import RAGService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PDF_URL = "https://cdnbbsr.s3waas.gov.in/s3ec012d95666e2649fcfc6e3af75e09f5/uploads/2025/04/20250419100.pdf"


async def main():
    logger.info(f"Ingesting: {PDF_URL}")
    rag = RAGService()

    result = await rag.ingest_document(PDF_URL)

    if result.get("success"):
        logger.info(f"✅ Ingestion successful. Chunks stored: {result.get('chunks_stored', 0)}")
    else:
        logger.error(f"❌ Ingestion failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    asyncio.run(main())

# ============================================================================
# Querying prompts
# ============================================================================

import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.rag_service import RAGService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TEST_QUERIES = [
    "What is this document about?",
    "List key deadlines or dates mentioned in the document.",
    "What actions are required from the applicant or citizen?",
    "Are there any eligibility criteria mentioned?",
    "Summarize the document in 5 bullet points.",
]


def main():
    rag = RAGService()

    for i, query in enumerate(TEST_QUERIES, 1):
        logger.info("=" * 70)
        logger.info(f"Q{i}: {query}")

        result = rag.search(query)

        if result.success:
            logger.info(f"✅ Chunks used: {result.chunk_count}")
            logger.info(f"Search queries: {result.search_queries}")
            logger.info(f"Answer:\n{result.answer}\n")
        else:
            logger.error(f"❌ Query failed: {result.error}")


if __name__ == "__main__":
    main()

# ============================================================================
# Querying prompts
# ============================================================================
