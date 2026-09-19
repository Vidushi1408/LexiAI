import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from generative import action_item_extractor as aie
from generative.quote_check import quote_in_text
from generative.schemas import ActionItemList, ActionItem
from llm import client

TEXT = "Priya will send the revised contract to legal by Friday. " * 2


def test_chat_json_validates_and_sends_schema():
    reply = '{"items": [{"task": "Send contract", "priority": "High"}]}'
    with patch("llm.client.chat", return_value=reply) as chat:
        res = client.chat_json("s", "u", ActionItemList)
    assert res.items[0].owner == "Unassigned"          # schema default applied
    assert chat.call_args.kwargs["schema"]["title"] == "ActionItemList"


def test_chat_json_repairs_prose_wrapped_json():
    reply = 'Sure! Here you go: {"items": []} hope that helps'
    with patch("llm.client.chat", return_value=reply):
        assert client.chat_json("s", "u", ActionItemList).items == []


def test_chat_json_returns_none_on_invalid_or_offline():
    with patch("llm.client.chat", return_value='{"items": [{"priority": "Urgent"}]}'):
        assert client.chat_json("s", "u", ActionItemList) is None
    with patch("llm.client.chat", return_value=None):
        assert client.chat_json("s", "u", ActionItemList) is None


def test_schema_rejects_bad_priority():
    with pytest.raises(ValidationError):
        ActionItem(task="x", priority="Urgent")


def test_action_items_from_llm():
    res = ActionItemList(items=[ActionItem(task="Send contract", priority="High", owner="Priya", deadline="Friday")])
    with patch.object(aie, "chat_json", return_value=res):
        assert aie.extract_action_items(TEXT)[0]["owner"] == "Priya"


def test_action_items_fallback_does_not_invent_owner_or_deadline():
    with patch.object(aie, "chat_json", return_value=None):
        items = aie.extract_action_items(TEXT)
    assert items and items[0]["owner"] == "Unassigned" and items[0]["deadline"] == "Not specified"


def test_quote_check():
    doc = "Either party may terminate this agreement\nwith ninety (90) days' written notice."
    assert quote_in_text("terminate this agreement with ninety (90) days written notice", doc)  # whitespace/quotes
    assert not quote_in_text("liability is capped at twelve months of fees", doc)
    assert not quote_in_text("too short", "too short indeed")
