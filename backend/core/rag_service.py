import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import openai
import cohere
import chromadb

from config.config import Settings
from utils.chunker import TableAwareChunker
from core.ocr_service import DocumentIntelligenceService

logging.basicConfig(level=logging.INFO)


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
    """Simple RAG pipeline service."""
    
    def __init__(self):
        settings = Settings()
        
        # LLM Client
        self.llm_client = openai.OpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url
        )
        
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

    # ============== Data Ingestion ==============
    
    async def ingest_document(self, pdf_blob_url: str) -> Dict[str, Any]:
        """
        Ingests a document: extracts, chunks, embeds, and stores.
        
        Args:
            pdf_blob_url: URL to the PDF blob
        """
        try:
            logging.info(f"Ingesting document: {pdf_blob_url}")
            
            # Extract content
            analysis_result = await self.doc_intel_client.analyze(pdf_blob_url, True)
            markdown_content = analysis_result["analyzeResult"]["content"]
            
            # Chunk content
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

    # ============== Query Parsing ==============
    
    def _parse_query(self, user_query: str) -> ReasoningQueryPlan:
        """Generates reasoning sub-questions from user query."""
        
        prompt = """You are a query analyzer. Given a user query, generate 2-3 reasoning sub-questions 
that would help better understand and answer the query.

Return a JSON object with:
- user_query: the original query
- reasoning_sub_questions: list of sub-questions"""

        response = self.llm_client.beta.chat.completions.parse(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_query}
            ],
            response_format=ReasoningQueryPlan
        )
        
        return response.choices[0].message.parsed

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

        response = self.llm_client.beta.chat.completions.parse(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Generate search queries."}
            ],
            response_format=SearchQueryPlan
        )
        
        return response.choices[0].message.parsed.search_queries

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

        response = self.llm_client.chat.completions.create(
            model="gemini-2.5-pro",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25
        )
        
        return response.choices[0].message.content or "Unable to generate answer."

    # ============== Main Search API ==============
    
    def search(self, user_query: str) -> RAGResponse:
        """
        Main search API: parses query, retrieves, and generates answer.
        """
        try:
            # Step 1: Parse query
            reasoning_plan = self._parse_query(user_query)
            
            # Step 2: Generate search queries
            search_queries = self._generate_search_queries(reasoning_plan)
            
            # Step 3: Retrieve and re-rank
            chunks = self._retrieve_and_rerank(search_queries)
            
            # Step 4: Generate answer
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