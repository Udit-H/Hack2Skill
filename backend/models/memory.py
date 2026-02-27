from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', or 'system'
    content: str

class ContextMemory(BaseModel):
    """
    Anthropic-style Memory Compaction.
    Instead of passing 50 messages, we pass the summary, the hard facts, and the last 3 messages.
    """
    long_term_summary: str = Field(
        default="New user session initiated.",
        description="A running 3-sentence summary of the case."
    )
    
    extracted_entities: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-Value pairs of established facts (e.g., {'landlord_name': 'Ramesh', 'rent': '15000'})"
    )
    
    short_term_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Only holds the last 4-5 conversational turns."
    )

    def to_xml_prompt(self) -> str:
        """Injects perfectly formatted XML context into the Jinja template."""
        history_xml = "\n".join([f"<{msg.role}>{msg.content}</{msg.role}>" for msg in self.short_term_history])
        
        entities_xml = "\n".join([f"<{k}>{v}</{k}>" for k, v in self.extracted_entities.items()])
        
        return f"""
<working_memory>
    <case_summary>{self.long_term_summary}</case_summary>
    <established_facts>
        {entities_xml if self.extracted_entities else "None"}
    </established_facts>
    <recent_chat_window>
        {history_xml if self.short_term_history else "No recent chat."}
    </recent_chat_window>
</working_memory>
"""