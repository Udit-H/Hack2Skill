import logging
import aiohttp
from typing import Optional
from config.config import get_settings

class RagFlowService:
    """Asynchronous client for RAGFlow to fetch Delhi-specific legal context."""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.ragflow.api_key
        self.base_url = self.settings.ragflow.endpoint
        self.dataset_id = self.settings.ragflow.delhi_law_dataset_id

    async def fetch_legal_context(self, query: str) -> Optional[str]:
        """Queries RAGFlow for statutes relevant to the user's crisis."""
        url = f"{self.base_url}/api/v1/retrieval"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "dataset_ids": [self.dataset_id],
            "question": query,
            "top_k": 3 # Keep context window small and relevant
        }

        logging.info(f"Querying RAGFlow for: {query}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
                    # Extract the concatenated text chunks from RAGFlow
                    return data.get("answer", "")
        except Exception as e:
            logging.error(f"RAGFlow retrieval failed: {e}")
            return "Legal context unavailable. Rely on general Delhi statutes."