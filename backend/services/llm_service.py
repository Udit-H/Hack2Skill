"""
Sahayak LLM Service
--------------------
Primary:  AWS Bedrock  (Llama 3 via Converse API)
Fallback: Groq         (Llama 3 via OpenAI-compatible API)

Every agent, the RAG pipeline, and the memory manager call this service
instead of touching LLM providers directly.
"""

import json
import logging
import asyncio
from typing import Type, TypeVar, List, Dict

import boto3
import instructor
from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel

from config.config import get_settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class LLMService:
    """
    Singleton LLM gateway with automatic Bedrock → Groq failover.

    Usage
    -----
        llm = LLMService()

        # Agents  (async, structured Pydantic output)
        state  = await llm.create_structured(TriageState, messages)

        # Memory  (async, plain text)
        text   = await llm.create_completion(messages)

        # RAG     (sync, structured)
        plan   = llm.create_structured_sync(ReasoningQueryPlan, messages)

        # RAG     (sync, plain text)
        answer = llm.create_completion_sync(messages)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        settings = get_settings()

        # ── Bedrock (primary) ────────────────────────────────────
        boto_kw: dict = {"region_name": settings.llm.aws_region}
        if settings.llm.aws_access_key_id:
            boto_kw["aws_access_key_id"] = settings.llm.aws_access_key_id
        if settings.llm.aws_secret_access_key:
            boto_kw["aws_secret_access_key"] = settings.llm.aws_secret_access_key

        self.bedrock = boto3.client("bedrock-runtime", **boto_kw)
        self.bedrock_model = settings.llm.bedrock_model_id

        # ── Groq (fallback) ─────────────────────────────────────
        groq_kw = dict(
            api_key=settings.llm.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self._groq_sync = OpenAI(**groq_kw)
        self._groq_async = AsyncOpenAI(**groq_kw)
        self.groq_model = settings.llm.groq_model_id

        self._groq_instr_sync = instructor.from_openai(
            self._groq_sync, mode=instructor.Mode.JSON
        )
        self._groq_instr_async = instructor.from_openai(
            self._groq_async, mode=instructor.Mode.JSON
        )

        logger.info(
            "✅ LLM Service ready — Bedrock (%s) → Groq (%s)",
            self.bedrock_model,
            self.groq_model,
        )

    # ================================================================
    #  PUBLIC — async structured output  (agents)
    # ================================================================

    async def create_structured(
        self,
        response_model: Type[T],
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> T:
        """Return a validated Pydantic model instance from the LLM."""
        try:
            result = await asyncio.to_thread(
                self._bedrock_structured,
                response_model,
                messages,
                temperature,
                max_tokens,
            )
            logger.info("  ✅ Bedrock structured OK")
            return result
        except Exception as exc:
            logger.warning("  ⚠️  Bedrock structured failed (%s) → Groq", exc)
            result = await self._groq_instr_async.chat.completions.create(
                model=self.groq_model,
                response_model=response_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info("  ✅ Groq structured OK (fallback)")
            return result

    # ================================================================
    #  PUBLIC — async plain text  (memory summarization)
    # ================================================================

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5,
        max_tokens: int = 2048,
    ) -> str:
        """Return plain text from the LLM."""
        try:
            text = await asyncio.to_thread(
                self._bedrock_completion,
                messages,
                temperature,
                max_tokens,
            )
            logger.info("  ✅ Bedrock completion OK")
            return text
        except Exception as exc:
            logger.warning("  ⚠️  Bedrock completion failed (%s) → Groq", exc)
            resp = await self._groq_async.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info("  ✅ Groq completion OK (fallback)")
            return resp.choices[0].message.content

    # ================================================================
    #  PUBLIC — sync structured output  (RAG query parsing)
    # ================================================================

    def create_structured_sync(
        self,
        response_model: Type[T],
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> T:
        """Synchronous variant for RAG pipeline."""
        try:
            result = self._bedrock_structured(
                response_model, messages, temperature, max_tokens,
            )
            logger.info("  ✅ Bedrock structured OK (sync)")
            return result
        except Exception as exc:
            logger.warning("  ⚠️  Bedrock structured failed (%s) → Groq (sync)", exc)
            result = self._groq_instr_sync.chat.completions.create(
                model=self.groq_model,
                response_model=response_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info("  ✅ Groq structured OK (sync fallback)")
            return result

    # ================================================================
    #  PUBLIC — sync plain text  (RAG answer generation)
    # ================================================================

    def create_completion_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.25,
        max_tokens: int = 2048,
    ) -> str:
        """Synchronous variant for RAG pipeline."""
        try:
            text = self._bedrock_completion(messages, temperature, max_tokens)
            logger.info("  ✅ Bedrock completion OK (sync)")
            return text
        except Exception as exc:
            logger.warning("  ⚠️  Bedrock completion failed (%s) → Groq (sync)", exc)
            resp = self._groq_sync.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info("  ✅ Groq completion OK (sync fallback)")
            return resp.choices[0].message.content

    # ================================================================
    #  BEDROCK INTERNALS
    # ================================================================

    def _to_bedrock_format(self, messages: List[Dict[str, str]]):
        """Convert OpenAI-style messages → Bedrock Converse API format.

        • system messages  → collected into the top-level ``system`` param
        • consecutive same-role messages → merged (Bedrock requires alternating roles)
        """
        bedrock_msgs: list = []
        system_text = None

        for msg in messages:
            role, content = msg["role"], msg["content"]
            if role == "system":
                system_text = f"{system_text}\n\n{content}" if system_text else content
            else:
                # Merge consecutive same-role messages
                if bedrock_msgs and bedrock_msgs[-1]["role"] == role:
                    bedrock_msgs[-1]["content"][0]["text"] += "\n\n" + content
                else:
                    bedrock_msgs.append(
                        {"role": role, "content": [{"text": content}]}
                    )

        return bedrock_msgs, system_text

    # ── structured (JSON schema injection) ───────────────────────

    def _bedrock_structured(
        self,
        response_model: Type[T],
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> T:
        bedrock_msgs, system_text = self._to_bedrock_format(messages)

        # Inject JSON-schema instruction into the last user turn
        schema = response_model.model_json_schema()
        instruction = (
            "\n\n--- OUTPUT FORMAT ---\n"
            "Respond with ONLY valid JSON matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n"
            "Rules:\n"
            "• Output pure JSON only — no markdown fences, no commentary.\n"
            "• For enum fields use the exact lowercase values from the schema.\n"
            "• Include ALL required fields.\n"
        )

        if bedrock_msgs and bedrock_msgs[-1]["role"] == "user":
            bedrock_msgs[-1]["content"][0]["text"] += instruction
        else:
            bedrock_msgs.append({"role": "user", "content": [{"text": instruction}]})

        req = {
            "modelId": self.bedrock_model,
            "messages": bedrock_msgs,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
                "topP": 0.9,
            },
        }
        if system_text:
            req["system"] = [{"text": system_text}]

        resp = self.bedrock.converse(**req)
        raw = resp["output"]["message"]["content"][0]["text"].strip()

        # Strip code fences the model sometimes adds
        for prefix in ("```json", "```"):
            if raw.startswith(prefix):
                raw = raw[len(prefix) :]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        data = json.loads(raw)
        data = self._normalise_enums(data, schema)
        return response_model(**data)

    # ── plain text ───────────────────────────────────────────────

    def _bedrock_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        bedrock_msgs, system_text = self._to_bedrock_format(messages)

        req = {
            "modelId": self.bedrock_model,
            "messages": bedrock_msgs,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system_text:
            req["system"] = [{"text": system_text}]

        resp = self.bedrock.converse(**req)
        return resp["output"]["message"]["content"][0]["text"]

    # ================================================================
    #  HELPERS
    # ================================================================

    @staticmethod
    def _normalise_enums(data: dict, schema: dict) -> dict:
        """Map UPPER_CASE enum names → lowercase values that Pydantic expects."""
        props = schema.get("properties", {})
        defs = schema.get("$defs", {})

        def _enum_values(fs):
            if "enum" in fs:
                return fs["enum"]
            if "$ref" in fs:
                ref = fs["$ref"].split("/")[-1]
                return defs.get(ref, {}).get("enum", [])
            for opt in fs.get("anyOf", []):
                v = _enum_values(opt)
                if v:
                    return v
            return []

        for key, val in list(data.items()):
            if isinstance(val, str) and key in props:
                allowed = _enum_values(props[key])
                if allowed and val not in allowed:
                    hit = [e for e in allowed if e.lower() == val.lower()]
                    if hit:
                        data[key] = hit[0]

        return data
