import os
import asyncio
import redis
import boto3
import json
import time
import logging
import jinja2
from botocore.exceptions import ClientError

from config.config import Settings
from config.config import get_settings
from core.bedrock_client import BedrockAsyncClient
from services.llm_service import LLMService

WORKING_MEMORY_TURNS = 6
SUMMARIZATION_THRESHOLD = WORKING_MEMORY_TURNS * 2
# DynamoDB: recent window to show + older messages get summarized
DYNAMO_RECENT_WINDOW = 8
DYNAMO_SUMMARIZE_AFTER = 12  # trigger summarization when total messages exceed this

prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=prompt_dir))
logger = logging.getLogger(__name__)
    


class MemoryManager:
    def __init__(self, session_id: str = None):
        settings = Settings()
        self.session_id = session_id
        self.memory_backend = os.getenv("MEMORY_BACKEND", "dynamodb").strip().lower()

        self.redis_client = None
        self.dynamodb_table = None

        if self.memory_backend == "redis":
            redis_kwargs = {
                "host": settings.redisdb.host,
                "port": settings.redisdb.port,
                "decode_responses": True,
                "password": settings.redisdb.password,
                "ssl": settings.redisdb.ssl,
            }
            if settings.redisdb.username:
                redis_kwargs["username"] = settings.redisdb.username

            self.redis_client = redis.Redis(**redis_kwargs)
        else:
            table_name = os.getenv("DYNAMODB_CHAT_TABLE", "sahayak-chat-messages")
            dynamodb = boto3.resource(
                "dynamodb",
                region_name=settings.llm.aws_region,
                aws_access_key_id=settings.llm.aws_access_key_id,
                aws_secret_access_key=settings.llm.aws_secret_access_key,
            )
            self.dynamodb_table = dynamodb.Table(table_name)
            # Summary table for L2 episodic memory (DynamoDB mode)
            summary_table_name = os.getenv("DYNAMODB_SUMMARY_TABLE", "sahayak-session-summaries")
            self.summary_table = dynamodb.Table(summary_table_name)
            self._turn_count = 0  # Track turns per session for summarization trigger
        
        self.llm = LLMService()
        
        self.template = template_env.get_template("memory.j2")

        self.working_memory_key = f"session:{session_id}:working_memory"
        self.episodic_memory_key = f"session:{session_id}:episodic_memory"

    def add_turn(self, user_message: str, ai_message: str):
        """
        Adds turns to memory.
        Redis: pushes to list, triggers L2 summarization at threshold.
        DynamoDB: tracks turn count, triggers L2 summarization at threshold.
        (DynamoDB messages are persisted by ChatStorageService in main.py — not here.)
        """
        if self.memory_backend == "redis":
            # 1. Push to Redis (Fast)
            self.redis_client.lpush(self.working_memory_key, f"AI: {ai_message}")
            self.redis_client.lpush(self.working_memory_key, f"User: {user_message}")
            
            # 2. Check length
            history_length = self.redis_client.llen(self.working_memory_key)
            
            # 3. BACKGROUND SUMMARIZATION (Does not block the user's response)
            if history_length >= SUMMARIZATION_THRESHOLD:
                asyncio.create_task(self._async_trigger_summary())
        else:
            # DynamoDB mode: messages are stored by ChatStorageService.
            # We just track turns to trigger L2 summarization.
            self._turn_count += 1
            if self._turn_count >= DYNAMO_SUMMARIZE_AFTER // 2:
                self._turn_count = 0
                asyncio.create_task(self._async_summarize_dynamodb())

    def get_memory_context(self) -> str:
        """
        Returns XML-tagged memory with long-term summary + recent chat history.
        Both Redis and DynamoDB modes now support L2 summarization.
        """
        if self.memory_backend == "redis":
            working_memory = self._get_working_memory()
            episodic_summary = self.redis_client.get(self.episodic_memory_key) or "No previous context. This is the start of the conversation."
        else:
            working_memory = self._get_working_memory_dynamodb()
            episodic_summary = self._get_dynamodb_summary()

        # XML boundaries prevent the LLM from confusing memory with instructions
        return f"""
<long_term_summary>
{episodic_summary}
</long_term_summary>

<recent_chat_history>
{working_memory}
</recent_chat_history>
"""

    def _get_working_memory(self) -> str:
        history = self.redis_client.lrange(self.working_memory_key, 0, -1)
        return "\n".join(reversed(history))

    def _get_working_memory_dynamodb(self) -> str:
        if not self.dynamodb_table:
            return ""

        try:
            response = self.dynamodb_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("session_id").eq(self.session_id),
                Limit=12,
                ScanIndexForward=False,
            )
            items = response.get("Items", [])
            items.reverse()

            lines = []
            for item in items:
                role = (item.get("role") or "assistant").strip().lower()
                prefix = "User" if role == "user" else "AI"
                content = item.get("content", "")
                if content:
                    lines.append(f"{prefix}: {content}")

            return "\n".join(lines)
        except ClientError as e:
            print(f"[Memory] DynamoDB memory read error: {e.response['Error']['Message']}")
            return ""
        except Exception as e:
            print(f"[Memory] Unexpected DynamoDB memory error: {e}")
            return ""
    
    async def _async_trigger_summary(self):
        """
        Redis L2 summarization — runs asynchronously.
        """
        if self.memory_backend != "redis":
            return

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

    # ================================================================
    #  DynamoDB L2 Summarization
    # ================================================================

    def _get_dynamodb_summary(self) -> str:
        """Read the L2 episodic summary from DynamoDB summary table."""
        if not self.summary_table:
            return "No previous context. This is the start of the conversation."
        try:
            resp = self.summary_table.get_item(Key={"session_id": self.session_id})
            item = resp.get("Item")
            if item and item.get("summary"):
                return item["summary"]
        except Exception as e:
            logger.warning(f"[Memory] Summary read error: {e}")
        return "No previous context. This is the start of the conversation."

    def _save_dynamodb_summary(self, summary: str):
        """Write the L2 episodic summary to DynamoDB summary table."""
        if not self.summary_table:
            return
        try:
            self.summary_table.put_item(Item={
                "session_id": self.session_id,
                "summary": summary,
                "updated_at": str(int(time.time())),
            })
        except Exception as e:
            logger.warning(f"[Memory] Summary write error: {e}")

    async def _async_summarize_dynamodb(self):
        """
        DynamoDB L2 summarization — runs asynchronously.
        Reads ALL messages from DynamoDB, summarizes the older ones,
        stores summary in the summary table. Next get_memory_context()
        will return summary + recent window (fewer tokens for Bedrock).
        """
        logger.info(f"[Background Task] DynamoDB L2 Summarization for {self.session_id}...")
        try:
            # Read all messages for this session
            response = self.dynamodb_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("session_id").eq(self.session_id),
                ScanIndexForward=True,  # oldest first
            )
            items = response.get("Items", [])

            if len(items) < DYNAMO_SUMMARIZE_AFTER:
                return  # Not enough messages to summarize yet

            # Split: older messages get summarized, recent stay as working memory
            older = items[:-DYNAMO_RECENT_WINDOW]
            
            if not older:
                return

            # Build text from older messages
            older_text = "\n".join([
                f"{'User' if item.get('role') == 'user' else 'AI'}: {item.get('content', '')}"
                for item in older if item.get('content')
            ])

            current_summary = self._get_dynamodb_summary()
            if current_summary == "No previous context. This is the start of the conversation.":
                current_summary = ""

            prompt = self.template.render(
                current_summary=current_summary,
                new_lines=older_text,
            )

            new_summary = await self.llm.create_completion(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Give me an updated summary using all the relevant context given in the system prompt"}
                ]
            )

            self._save_dynamodb_summary(new_summary)
            logger.info(f"[Background Task] DynamoDB summarization complete ({len(older)} messages → summary)")

        except Exception as e:
            logger.error(f"[Background Task] DynamoDB summarization error: {e}")