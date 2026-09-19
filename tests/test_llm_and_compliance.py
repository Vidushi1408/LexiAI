import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
import requests

from llm import client
from generative import quiz_generator
from generative.schemas import ComplianceReport, ComplianceFinding


def _resp(status, body=None):
    r = MagicMock(status_code=status, text="")
    r.json.return_value = body or {}
    return r


def test_chat_returns_stripped_text():
    with patch("llm.client.requests.post", return_value=_resp(200, {"message": {"content": " hi "}})):
        assert client.chat("sys", "user") == "hi"


def test_chat_returns_none_when_ollama_down():
    with patch("llm.client.requests.post", side_effect=requests.exceptions.ConnectionError):
        assert client.chat("sys", "user") is None


def test_chat_does_not_retry_client_errors():
    with patch("llm.client.requests.post", return_value=_resp(404)) as post:
        assert client.chat("sys", "user") is None
        assert post.call_count == 1


def test_chat_retries_server_errors():
    with patch("llm.client.requests.post", return_value=_resp(500)) as post, \
         patch("llm.client.time.sleep"):
        assert client.chat("sys", "user") is None
        assert post.call_count == client.settings.llm_retries + 1


DOC = ["Either party may terminate this agreement with ninety days written notice.",
       "Payment is due within thirty days of the invoice date."]


def _report(*findings):
    return ComplianceReport(items=[ComplianceFinding(recommendation="r", explanation="e", **f) for f in findings])


def test_pass_with_verified_quote_is_kept():
    rep = _report({"requirement": "Termination", "status": "PASS",
                   "quote": "terminate this agreement with ninety days written notice"})
    with patch.object(quiz_generator, "chat_json", return_value=rep):
        item = quiz_generator.evaluate_compliance(DOC)[0]
    assert item["status"] == "PASS" and item["quote_verified"]


def test_pass_with_fabricated_quote_is_downgraded_to_review():
    rep = _report({"requirement": "Liability", "status": "PASS",
                   "quote": "Liability is capped at twelve months of fees"})
    with patch.object(quiz_generator, "chat_json", return_value=rep):
        item = quiz_generator.evaluate_compliance(DOC)[0]
    assert item["status"] == "REVIEW" and not item["quote_verified"]
    assert item["citation"] == "Section Not Found"


def test_review_without_quote_stays_review():
    rep = _report({"requirement": "SLA", "status": "REVIEW", "quote": ""})
    with patch.object(quiz_generator, "chat_json", return_value=rep):
        assert quiz_generator.evaluate_compliance(DOC)[0]["status"] == "REVIEW"


def test_compliance_falls_back_to_real_quotes_when_llm_offline():
    with patch.object(quiz_generator, "chat_json", return_value=None):
        items = quiz_generator.evaluate_compliance(DOC)
    by_req = {i["requirement"]: i for i in items}
    assert by_req["Payment Terms & Penalties"]["status"] == "PASS"
    assert by_req["Payment Terms & Penalties"]["citation"] == DOC[1]
    assert by_req["Limitation of Liability & Indemnity"]["status"] == "REVIEW"


def test_policy_file_loads():
    policy = quiz_generator.load_policy()
    assert policy["version"] and len(policy["requirements"]) == 6
