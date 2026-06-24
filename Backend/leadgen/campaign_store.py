import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

CAMPAIGNS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "leadgen_campaigns.json")
LEADS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "leadgen_leads")


def _ensure_dirs():
    os.makedirs(os.path.dirname(CAMPAIGNS_FILE), exist_ok=True)
    os.makedirs(LEADS_DIR, exist_ok=True)


def _load_campaigns() -> list[dict]:
    _ensure_dirs()
    if not os.path.exists(CAMPAIGNS_FILE):
        return []
    with open(CAMPAIGNS_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_campaigns(campaigns: list[dict]):
    _ensure_dirs()
    with open(CAMPAIGNS_FILE, "w") as f:
        json.dump(campaigns, f, indent=2, default=str)


def create_campaign(name: str, description: str, keywords: list[str], platforms: list[str], enrichment: Optional[dict] = None) -> dict:
    campaigns = _load_campaigns()
    campaign = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "keywords": keywords,
        "competitor_keywords": (enrichment or {}).get("competitor_keywords", []),
        "platform": platforms[0] if platforms else "twitter",
        "platforms": platforms,
        "target_audience": (enrichment or {}).get("target_audience", ""),
        "intent_queries": (enrichment or {}).get("intent_queries", []),
        "pain_points": (enrichment or {}).get("pain_points", []),
        "steal_audience_angle": (enrichment or {}).get("steal_audience_angle", ""),
        "enriched": enrichment or {},
        "website_url": (enrichment or {}).get("website_url", ""),
        "competitor_tracking": (enrichment or {}).get("competitor_tracking", []),
        "viral_content_angles": (enrichment or {}).get("viral_content_angles", []),
        "value_proposition": (enrichment or {}).get("value_proposition", ""),
        "competitors": [],
        "viral_posts": [],
        "alert_settings": {"email": "", "slack": "", "enabled": False},
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "lead_count": 0,
    }
    campaigns.insert(0, campaign)
    _save_campaigns(campaigns)
    return campaign


def get_campaigns() -> list[dict]:
    return _load_campaigns()


def get_campaign(campaign_id: str) -> Optional[dict]:
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            return c
    return None


def update_campaign(campaign_id: str, updates: dict) -> Optional[dict]:
    campaigns = _load_campaigns()
    for i, c in enumerate(campaigns):
        if c["id"] == campaign_id:
            campaigns[i].update(updates)
            _save_campaigns(campaigns)
            return campaigns[i]
    return None


def delete_campaign(campaign_id: str) -> bool:
    campaigns = _load_campaigns()
    filtered = [c for c in campaigns if c["id"] != campaign_id]
    if len(filtered) == len(campaigns):
        return False
    _save_campaigns(filtered)
    leads_file = os.path.join(LEADS_DIR, f"{campaign_id}.json")
    if os.path.exists(leads_file):
        os.remove(leads_file)
    return True


def add_competitor(campaign_id: str, competitor: dict) -> Optional[dict]:
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            competitor["id"] = str(uuid.uuid4())
            competitor["added_at"] = datetime.now(timezone.utc).isoformat()
            if "competitors" not in c:
                c["competitors"] = []
            c["competitors"].append(competitor)
            _save_campaigns(campaigns)
            return competitor
    return None


def remove_competitor(campaign_id: str, competitor_id: str) -> bool:
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            before = len(c.get("competitors", []))
            c["competitors"] = [comp for comp in c.get("competitors", []) if comp.get("id") != competitor_id]
            if len(c["competitors"]) < before:
                _save_campaigns(campaigns)
                return True
    return False


def add_viral_post(campaign_id: str, post: dict) -> Optional[dict]:
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            post["id"] = str(uuid.uuid4())
            post["saved_at"] = datetime.now(timezone.utc).isoformat()
            if "viral_posts" not in c:
                c["viral_posts"] = []
            c["viral_posts"].insert(0, post)
            _save_campaigns(campaigns)
            return post
    return None


def add_lead(campaign_id: str, lead: dict) -> dict:
    _ensure_dirs()
    leads_file = os.path.join(LEADS_DIR, f"{campaign_id}.json")
    leads = []
    if os.path.exists(leads_file):
        with open(leads_file) as f:
            try:
                leads = json.load(f)
            except json.JSONDecodeError:
                leads = []
    lead["id"] = str(uuid.uuid4())
    lead["campaign_id"] = campaign_id
    lead["created_at"] = datetime.now(timezone.utc).isoformat()
    leads.insert(0, lead)
    with open(leads_file, "w") as f:
        json.dump(leads, f, indent=2, default=str)
    campaigns = _load_campaigns()
    for c in campaigns:
        if c["id"] == campaign_id:
            c["lead_count"] = len(leads)
            break
    _save_campaigns(campaigns)
    return lead


def get_leads(campaign_id: str) -> list[dict]:
    _ensure_dirs()
    leads_file = os.path.join(LEADS_DIR, f"{campaign_id}.json")
    if not os.path.exists(leads_file):
        return []
    with open(leads_file) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []
