from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Lead:
    id: str
    platform: str
    external_id: Optional[str] = None
    username: str = ""
    display_name: Optional[str] = None
    profile_url: str = ""
    avatar_url: Optional[str] = None
    post_url: Optional[str] = None
    post_text: Optional[str] = None
    post_timestamp: Optional[datetime] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    bio: Optional[str] = None
    email: Optional[str] = None
    is_verified: bool = False
    source: str = ""
    intent_score: float = 0.0
    status: str = "new"
    raw_data: dict = field(default_factory=dict)


@dataclass
class Campaign:
    id: str
    name: str = ""
    keywords: list[str] = field(default_factory=list)
    competitor_keywords: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    target_audience: str = ""
    engine: str = "devtools"
    apify_api_key: Optional[str] = None
    engagement_mode: str = "manual"
    status: str = "active"
    created_at: Optional[datetime] = None
    chrome_port: int = 9222


@dataclass
class Engagement:
    id: str
    lead_id: str
    campaign_id: str
    type: str = "comment"
    message: str = ""
    ai_generated_message: Optional[str] = None
    status: str = "draft"
    magicsync_post_id: Optional[str] = None
    created_at: Optional[datetime] = None


Platforms = ["twitter", "instagram", "tiktok", "youtube", "facebook"]
Engines = ["apify", "scrapling", "devtools"]
EngagementModes = ["manual", "auto"]
LeadStatuses = ["new", "contacted", "replied", "ignored"]
