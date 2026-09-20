# auth/roles.py
"""Role -> permitted pages. Roles are cumulative: viewer < analyst < admin."""

VIEWER_PAGES = [
    "🏠 Landing Page", "📊 Executive Dashboard", "💬 Document Q&A", "🔎 Hybrid Search", "💳 Billing & Pricing",
]
ANALYST_PAGES = [
    "📚 Knowledge Base & Upload", "📋 Executive Briefings", "✅ Compliance Checker",
    "🏷️ Entity & Clause Extraction", "⚡ Action Item Extractor", "📁 Document Clustering & Tagging",
]
ADMIN_PAGES = ["🛡️ Audit Log", "⚙️ Settings"]


def allowed_pages(role: str, all_pages: list[str]) -> list[str]:
    allowed = set(VIEWER_PAGES)
    if role in ("analyst", "admin"):
        allowed |= set(ANALYST_PAGES)
    if role == "admin":
        allowed |= set(ADMIN_PAGES)
    return [p for p in all_pages if p in allowed]


def can_upload(role: str) -> bool:
    return role in ("analyst", "admin")


def is_admin(role: str) -> bool:
    return role == "admin"
