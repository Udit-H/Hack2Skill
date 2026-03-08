import logging
import re
import os
import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import cohere
import chromadb
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse

from config.config import Settings
from services.llm_service import LLMService
from utils.chunker import TableAwareChunker
from services.ocr_service import DocumentIntelligenceService

logging.basicConfig(level=logging.INFO)

# ============== RAG Retrieval Cache ==============
# Caches the expensive retrieval pipeline (embed → search → rerank)
# in DynamoDB so repeated/similar legal queries skip Cohere + ChromaDB entirely.
# The final answer is still generated fresh per-user by the LLM.

RAG_CACHE_TTL = int(os.getenv("RAG_CACHE_TTL", 86400))  # 24 hours default


def _rag_cache_key(query: str) -> str:
    """Normalize query and produce a stable hash for cache lookup."""
    normalized = re.sub(r"\s+", " ", query.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


# ============== Pydantic Models ==============

class ReasoningQueryPlan(BaseModel):
    """Plan for reasoning about a user query."""
    user_query: str = Field(description="The original user query")
    reasoning_sub_questions: List[str] = Field(default_factory=list, description="Sub-questions to reason about")
    reasoning_responses: List[str] = Field(default_factory=list, description="Responses to reasoning questions")


class SearchQueryPlan(BaseModel):
    """Plan for searching the vector database."""
    user_query: str = Field(description="The original user query")
    search_queries: List[str] = Field(default_factory=list, description="Queries for vector search")


class RetrievalResult(BaseModel):
    """Result from retrieval and re-ranking."""
    score: float
    query: str
    content: str


class RAGResponse(BaseModel):
    """Final response from RAG pipeline."""
    success: bool
    answer: Optional[str] = None
    reasoning_questions: List[str] = Field(default_factory=list)
    search_queries: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    error: Optional[str] = None


# ============== RAG Service ==============

class RAGService:
    """Simple RAG pipeline service with DynamoDB retrieval caching."""
    
    def __init__(self):
        settings = Settings()
        
        # LLM Client (Bedrock → Groq fallback)
        self.llm = LLMService()
        
        # Cohere Client
        self.cohere_client = cohere.Client(api_key=settings.cohere.api_key)
        self.async_cohere_client = cohere.AsyncClient(api_key=settings.cohere.api_key)
        
        # ChromaDB
        chroma_client = chromadb.HttpClient(
            ssl=True,
            host='api.trychroma.com',
            tenant=settings.chromadb.tenant,
            database=settings.chromadb.database,
            headers={'x-chroma-token': settings.chromadb.token}
        )
        self.collection = chroma_client.get_or_create_collection(name="hackrx-sections")
        
        # Document Intelligence & Chunker
        self.doc_intel_client = DocumentIntelligenceService()
        self.chunker = TableAwareChunker(child_chunk_size=512)

        # ── RAG Retrieval Cache (DynamoDB) ──
        self._cache_table = None
        try:
            cache_table_name = os.getenv("RAG_CACHE_TABLE", "sahayak-rag-cache")
            dynamodb = boto3.resource(
                "dynamodb",
                region_name=settings.llm.aws_region,
                aws_access_key_id=settings.llm.aws_access_key_id,
                aws_secret_access_key=settings.llm.aws_secret_access_key,
            )
            self._cache_table = dynamodb.Table(cache_table_name)
            # Quick validation — will fail silently if table doesn't exist
            self._cache_table.table_status
            logging.info(f"✅ RAG cache enabled (table: {cache_table_name})")
        except Exception as e:
            self._cache_table = None
            logging.warning(f"⚠️  RAG cache disabled — DynamoDB table not available: {e}")

    # ============== RAG Cache Helpers ==============

    def _cache_get(self, query: str) -> Optional[List[Dict]]:
        """Look up cached retrieval results for a query. Returns None on miss."""
        if not self._cache_table:
            return None
        try:
            key = _rag_cache_key(query)
            resp = self._cache_table.get_item(Key={"query_hash": key})
            item = resp.get("Item")
            if not item:
                return None
            # Check TTL
            if item.get("expires_at", 0) < int(time.time()):
                logging.info(f"  🔄 RAG cache expired for query hash {key[:8]}...")
                return None
            logging.info(f"  💰 RAG cache HIT — skipping embed + search + rerank")
            return json.loads(item["chunks_json"])
        except Exception as e:
            logging.warning(f"  ⚠️  RAG cache read error: {e}")
            return None

    def _cache_put(self, query: str, chunks: List[Dict]):
        """Store retrieval results in the cache."""
        if not self._cache_table:
            return
        try:
            key = _rag_cache_key(query)
            self._cache_table.put_item(Item={
                "query_hash": key,
                "query_text": query[:500],  # Store truncated query for debugging
                "chunks_json": json.dumps(chunks),
                "expires_at": int(time.time()) + RAG_CACHE_TTL,
                "created_at": int(time.time()),
            })
            logging.info(f"  💾 RAG cache stored ({len(chunks)} chunks)")
        except Exception as e:
            logging.warning(f"  ⚠️  RAG cache write error: {e}")

    # ============== Data Ingestion ==============

    @staticmethod
    def _is_pdf_url(url: str) -> bool:
        path = urlparse(url).path.lower()
        return path.endswith(".pdf")
    
    async def ingest_document(self, pdf_blob_url: str) -> Dict[str, Any]:
        """
        Ingests a document: extracts, chunks, embeds, and stores.
        
        Args:
            pdf_blob_url: URL to the PDF blob
        """
        try:
            logging.info(f"Ingesting document: {pdf_blob_url}")

            analysis_result = await self.doc_intel_client.analyze(pdf_blob_url, is_url=True)

            markdown_content = (
                analysis_result.get("analyzeResult", {}).get("content")
                or analysis_result.get("content", "")
            )
            if not markdown_content.strip():
                raise ValueError("OCR returned empty content")

            child_chunks, _ = await self.chunker.process_document(markdown_content)
            
            # Generate embeddings
            content_list = [doc['content'] for doc in child_chunks]
            
            try:
                resp = await self.async_cohere_client.embed(
                    model="embed-english-v3.0",
                    input_type="search_document",
                    texts=content_list,
                    embedding_types=["float"]
                )
            except Exception:
                resp = await self.async_cohere_client.embed(
                    model="embed-multilingual-v3.0",
                    input_type="search_document",
                    texts=content_list,
                    embedding_types=["float"]
                )
            
            # Store in ChromaDB
            self.collection.add(
                ids=[doc["child_id"] for doc in child_chunks],
                embeddings=resp.embeddings.float,
                documents=content_list,
                metadatas=[doc['metadata'] for doc in child_chunks]
            )
            
            logging.info("Document ingestion complete.")
            return {"success": True, "chunks_stored": len(child_chunks)}
        
        except Exception as e:
            logging.error(f"Ingestion failed: {e}")
            return {"success": False, "error": str(e)}

    async def ingest_text(self, markdown_content: str, source: str, doc_type: str = "legal") -> Dict[str, Any]:
        """
        Ingests plain text/markdown content directly into ChromaDB (bypasses OCR).
        Use this for curated knowledge base documents.

        Args:
            markdown_content: The markdown/text content to ingest
            source: Source identifier (e.g., "PWDVA 2005")
            doc_type: Document category tag (e.g., "bare_act", "procedure", "resource")
        """
        try:
            logging.info(f"Ingesting text document: {source}")
            if not markdown_content.strip():
                raise ValueError("Content is empty")

            # Create unique prefix from source to avoid ID collisions across documents
            slug = re.sub(r'[^a-z0-9]+', '_', source.lower()).strip('_')[:30]

            child_chunks, _ = await self.chunker.process_document(markdown_content)

            if not child_chunks:
                raise ValueError("No chunks produced from content")

            # Prefix IDs and add source metadata
            for chunk in child_chunks:
                chunk['child_id'] = f"{slug}_{chunk['child_id']}"
                chunk['metadata']['source'] = source
                chunk['metadata']['doc_type'] = doc_type
                chunk['metadata']['parent_id'] = f"{slug}_{chunk['metadata']['parent_id']}"

            content_list = [doc['content'] for doc in child_chunks]

            # Embed in batches (Cohere limit ~96 texts per call)
            BATCH_SIZE = 96
            all_embeddings = []
            for i in range(0, len(content_list), BATCH_SIZE):
                batch = content_list[i:i + BATCH_SIZE]
                try:
                    resp = await self.async_cohere_client.embed(
                        model="embed-english-v3.0",
                        input_type="search_document",
                        texts=batch,
                        embedding_types=["float"]
                    )
                except Exception:
                    resp = await self.async_cohere_client.embed(
                        model="embed-multilingual-v3.0",
                        input_type="search_document",
                        texts=batch,
                        embedding_types=["float"]
                    )
                all_embeddings.extend(resp.embeddings.float)

            # Upsert into ChromaDB in batches (handles re-ingestion gracefully)
            CHROMA_BATCH = 100
            for i in range(0, len(child_chunks), CHROMA_BATCH):
                end = min(i + CHROMA_BATCH, len(child_chunks))
                self.collection.upsert(
                    ids=[doc["child_id"] for doc in child_chunks[i:end]],
                    embeddings=all_embeddings[i:end],
                    documents=content_list[i:end],
                    metadatas=[doc['metadata'] for doc in child_chunks[i:end]]
                )

            logging.info(f"Text ingestion complete: {len(child_chunks)} chunks from '{source}'")
            return {"success": True, "chunks_stored": len(child_chunks), "source": source}

        except Exception as e:
            logging.error(f"Text ingestion failed for '{source}': {e}")
            return {"success": False, "error": str(e), "source": source}

    # ============== Query Parsing ==============
    
    def _parse_query(self, user_query: str) -> ReasoningQueryPlan:
        """Generates reasoning sub-questions from user query."""
        
        prompt = """You are a query analyzer. Given a user query, generate 2-3 reasoning sub-questions 
that would help better understand and answer the query.

Return a JSON object with:
- user_query: the original query
- reasoning_sub_questions: list of sub-questions"""

        return self.llm.create_structured_sync(
            response_model=ReasoningQueryPlan,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_query}
            ],
        )

    # ============== Search Query Generation ==============
    
    def _generate_search_queries(self, reasoning_plan: ReasoningQueryPlan) -> List[str]:
        """Generates search queries from reasoning plan."""
        
        prompt = f"""Based on the user query and reasoning questions, generate 3-5 search queries 
for retrieving relevant information from a vector database.

User Query: {reasoning_plan.user_query}
Reasoning Questions: {reasoning_plan.reasoning_sub_questions}

Return a JSON object with:
- user_query: the original query  
- search_queries: list of search queries"""

        plan = self.llm.create_structured_sync(
            response_model=SearchQueryPlan,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Generate search queries."}
            ],
        )
        
        return plan.search_queries

    # ============== Retrieval & Re-ranking ==============
    
    def _retrieve_and_rerank(self, search_queries: List[str]) -> List[RetrievalResult]:
        """Retrieves and re-ranks documents."""
        
        if not search_queries:
            return []
        
        # Generate query embeddings
        query_embeddings = self.cohere_client.embed(
            texts=search_queries,
            model="embed-english-v3.0",
            input_type="search_query",
            embedding_types=["float"]
        ).embeddings.float

        # Retrieve from ChromaDB
        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=12,
            include=["documents", "metadatas"]
        )

        # Flatten results
        all_docs = [doc for sublist in results["documents"] for doc in sublist]
        all_metas = [meta for sublist in results["metadatas"] for meta in sublist]
        
        # Prepare docs for re-ranking (use parent content for paragraphs)
        docs_for_rerank = []
        for i, meta in enumerate(all_metas):
            if meta.get("content_type") == "paragraph":
                docs_for_rerank.append(meta.get("full_parent_content", all_docs[i]))
            else:
                docs_for_rerank.append(all_docs[i])

        if not docs_for_rerank:
            return []

        # Re-rank
        final_results = []
        for query in search_queries:
            reranked = self.cohere_client.rerank(
                model="rerank-v3.5",
                query=query,
                documents=docs_for_rerank,
                top_n=4
            )
            for r in reranked.results:
                final_results.append(RetrievalResult(
                    score=r.relevance_score,
                    query=query,
                    content=docs_for_rerank[r.index]
                ))

        # Sort by score descending
        final_results.sort(key=lambda x: -x.score)
        return final_results

    # ============== Answer Generation ==============
    
    def _generate_answer(self, user_query: str, chunks: List[RetrievalResult], max_chunks: int = 5) -> str:
        """Generates answer from retrieved chunks."""
        
        if not chunks:
            return "I could not find relevant information to answer your question."

        context = "\n----\n".join([c.content for c in chunks[:max_chunks]])
        
        prompt = f"""Based on the following context, answer the user's question accurately and concisely.

Context:
{context}

Question: {user_query}

Provide a clear, helpful answer based only on the given context."""

        return self.llm.create_completion_sync(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25
        )

    # ============== Main Search API ==============
    
    def search(self, user_query: str) -> RAGResponse:
        """
        Main search API: parses query, retrieves (with caching), and generates answer.

        Cost optimization:
        - Steps 1-3 (parse → embed → search → rerank) are cached in DynamoDB.
        - On cache hit, we skip Cohere embed, ChromaDB search, and Cohere rerank entirely.
        - Step 4 (answer generation) always runs fresh so the answer is contextual.
        """
        try:
            # ── Check retrieval cache first ──
            cached = self._cache_get(user_query)
            if cached is not None:
                # Cache HIT: reconstruct RetrievalResult objects from cached dicts
                chunks = [RetrievalResult(**c) for c in cached]
                # Generate fresh answer using cached retrieval
                answer = self._generate_answer(user_query, chunks)
                return RAGResponse(
                    success=True,
                    answer=answer,
                    reasoning_questions=[],
                    search_queries=["(cached)"],
                    chunk_count=len(chunks),
                )

            # ── Cache MISS: full pipeline ──
            # Step 1: Parse query (1 LLM call)
            reasoning_plan = self._parse_query(user_query)
            
            # Step 2: Generate search queries (1 LLM call)
            search_queries = self._generate_search_queries(reasoning_plan)
            
            # Step 3: Retrieve and re-rank (Cohere embed + ChromaDB + Cohere rerank)
            chunks = self._retrieve_and_rerank(search_queries)

            # ── Store retrieval results in cache ──
            if chunks:
                self._cache_put(user_query, [c.model_dump() for c in chunks])
            
            # Step 4: Generate answer (1 LLM call — always fresh)
            answer = self._generate_answer(user_query, chunks)
            
            return RAGResponse(
                success=True,
                answer=answer,
                reasoning_questions=reasoning_plan.reasoning_sub_questions,
                search_queries=search_queries,
                chunk_count=len(chunks)
            )
        
        except Exception as e:
            logging.error(f"Search failed: {e}")
            return RAGResponse(success=False, error=str(e))