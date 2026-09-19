# generative/action_item_extractor.py
"""
Action Item Extractor — Lexi AI
---------------------------------
Extracts high, medium, and low priority tasks from transcripts, emails, and notes
with owner assignment, deadlines, and current status.
"""

import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ACTION_SYSTEM_PROMPT = """You are an executive operational assistant.

Extract all ACTION ITEMS and TASKS from the provided meeting transcript, email, or operational notes.

CATEGORIZE BY PRIORITY:
- "High": Urgent, critical path, legal, financial, or strict deadline within 48h/1 week.
- "Medium": Standard operational task, feature delivery, or routine follow-up.
- "Low": Research, optional review, or long-term backlogged item.

Return every task as an item with: task, priority (High/Medium/Low), owner (person or role named in the text, else "Unassigned"),
deadline (as stated in the text, else "Not specified"), status (Pending / In Progress / Done).
Only extract tasks that are actually stated in the text — never invent owners or deadlines."""


from llm.client import chat_json
from generative.schemas import ActionItemList


def extract_action_items(text: str) -> list:
    """
    Extracts action items categorized by High, Medium, Low priority with Owner, Deadline, Status.
    """
    if not text or len(text.strip()) < 30:
        return []

    user_msg = f"Extract all action items from this transcript/document:\n\n{text[:4000]}"
    result = chat_json(ACTION_SYSTEM_PROMPT, user_msg, ActionItemList, max_tokens=2000)
    if result is None or not result.items:
        return _fallback_action_extraction(text)
    return [item.model_dump() for item in result.items]


def _fallback_action_extraction(text: str) -> list:
    """Rule-based fallback action item extractor."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    items = []
    
    keywords = ["need to", "action item", "should", "will", "assigned to", "please", "deadline", "by next", "responsible for"]
    
    for s in sentences:
        sl = s.lower()
        if any(k in sl for k in keywords) and len(s.strip()) > 15:
            priority = "High" if any(h in sl for h in ["urgent", "asap", "critical", "immediately", "today"]) else ("Low" if "eventually" in sl or "optional" in sl else "Medium")
            items.append({
                "task": s.strip()[:120],
                "priority": priority,
                "owner": "Unassigned",
                "deadline": "Not specified",
                "status": "Pending"
            })
            if len(items) >= 6:
                break
                
    return items
