import os
import asyncio
import redis
import jinja2

from config.config import Settings
from services.llm_service import LLMService

WORKING_MEMORY_TURNS = 6
SUMMARIZATION_THRESHOLD = WORKING_MEMORY_TURNS * 2

prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=prompt_dir))
    


class MemoryManager:
    def __init__(self, session_id: str = None):
        settings = Settings()
        self.session_id = session_id
        
        self.redis_client = redis.Redis(
            host=settings.redisdb.host,
            port=settings.redisdb.port,
            decode_responses=True,
            username="default",
            password=settings.redisdb.password,
        )
        
        self.llm = LLMService()
        
        self.template = template_env.get_template("memory.j2")

        self.working_memory_key = f"session:{session_id}:working_memory"
        self.episodic_memory_key = f"session:{session_id}:episodic_memory"

    def add_turn(self, user_message: str, ai_message: str):
        """
        Adds turns to Redis instantly (0.001s latency).
        Fires off summarization in the background if threshold met.
        """
        # 1. Push to Redis (Fast)
        self.redis_client.lpush(self.working_memory_key, f"AI: {ai_message}")
        self.redis_client.lpush(self.working_memory_key, f"User: {user_message}")
        
        # 2. Check length
        history_length = self.redis_client.llen(self.working_memory_key)
        
        # 3. BACKGROUND SUMMARIZATION (Does not block the user's response)
        if history_length >= SUMMARIZATION_THRESHOLD:
            # For CLI testing, we use asyncio.create_task. 
            # Later, this exact line becomes: celery_summarize_task.delay(self.session_id)
            asyncio.create_task(self._async_trigger_summary())

    def get_memory_context(self) -> str:
        """
        Returns Anthropic-compliant XML tagged memory.
        """
        working_memory = self._get_working_memory()
        redis_summary = self.redis_client.get(self.episodic_memory_key) or "No previous context. This is the start of the conversation."

        # XML boundaries prevent the LLM from confusing memory with instructions
        return f"""
<long_term_summary>
{redis_summary}
</long_term_summary>

<recent_chat_history>
{working_memory}
</recent_chat_history>
"""

    def _get_working_memory(self) -> str:
        history = self.redis_client.lrange(self.working_memory_key, 0, -1)
        return "\n".join(reversed(history))
    
    async def _async_trigger_summary(self):
        """
        Runs asynchronously so the Orchestrator doesn't freeze.
        """
        print(f"\n[Background Task] Triggering L2 Summarization for {self.session_id}...")
        
        full_history = self._get_working_memory()
        current_summary = self.redis_client.get(self.episodic_memory_key) or ""
        
        prompt = self.template.render(
            current_summary=current_summary,
            new_lines=full_history
        )
        
        try:
            new_summary = await self.llm.create_completion(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Give me an updated summary using all the relevant context given in the system prompt"}
                ]
            )
            self.redis_client.set(self.episodic_memory_key, new_summary)
            
            # SLIDING WINDOW FIX: Do not delete everything! 
            self.redis_client.ltrim(self.working_memory_key, 0, 3)
            print(f"[Background Task] Summarization complete.")

        except Exception as e:
            print(f"[Background Task] Error during summarization: {e}")