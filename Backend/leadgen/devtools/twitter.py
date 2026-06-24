from datetime import datetime
from typing import Optional

from leadgen.schemas import Lead
from leadgen.devtools.connector import ChromeConnector


TWITTER_SEARCH_URL = "https://x.com/search?q={query}&src=typed_query&f=live"


async def search_tweets(keyword: str, max_results: int = 20, port: int = 9222) -> list[Lead]:
    connector = ChromeConnector(port=port)
    if not await connector.connect():
        raise ConnectionError(f"Could not connect to Chrome on port {port}. Is it running with --remote-debugging-port={port}?")
    try:
        await connector.create_session()
        url = TWITTER_SEARCH_URL.format(query=keyword.replace(" ", "%20"))
        await connector.navigate(url, wait_until="network_idle")
        await asyncio.sleep(3)
        await connector.scroll_down(times=2, delay=1.5)

        tweets = await connector.evaluate(_EXTRACT_TWEETS_JS)
        if not tweets:
            tweets = []
        leads = []
        for t in tweets[:max_results]:
            lead = _tweet_to_lead(t, keyword)
            if lead:
                leads.append(lead)
        return leads
    finally:
        await connector.close_session()
        await connector.disconnect()


async def get_profile(username: str, port: int = 9222) -> Optional[Lead]:
    connector = ChromeConnector(port=port)
    if not await connector.connect():
        raise ConnectionError(f"Could not connect to Chrome on port {port}.")
    try:
        await connector.create_session()
        url = f"https://x.com/{username}"
        await connector.navigate(url, wait_until="network_idle")
        await asyncio.sleep(3)

        profile = await connector.evaluate(_EXTRACT_PROFILE_JS)
        if profile:
            return _profile_to_lead(profile)
        return None
    finally:
        await connector.close_session()
        await connector.disconnect()


def _tweet_to_lead(t: dict, keyword: str) -> Optional[Lead]:
    if not t.get("tweetId"):
        return None
    return Lead(
        id=f"tw_{t['tweetId']}",
        platform="twitter",
        external_id=t["tweetId"],
        username=t.get("username", ""),
        display_name=t.get("displayName"),
        profile_url=f"https://x.com/{t.get('username', '')}",
        avatar_url=t.get("avatarUrl"),
        post_url=f"https://x.com/{t.get('username', '')}/status/{t['tweetId']}",
        post_text=t.get("text", ""),
        post_timestamp=_parse_twitter_time(t.get("timestamp")),
        follower_count=t.get("followers"),
        following_count=t.get("following"),
        bio=t.get("bio"),
        is_verified=t.get("verified", False),
        source="devtools",
        raw_data=t,
    )


def _profile_to_lead(p: dict) -> Lead:
    return Lead(
        id=f"tw_profile_{p.get('username', '')}",
        platform="twitter",
        external_id=p.get("userId"),
        username=p.get("username", ""),
        display_name=p.get("displayName"),
        profile_url=f"https://x.com/{p.get('username', '')}",
        avatar_url=p.get("avatarUrl"),
        bio=p.get("bio"),
        follower_count=p.get("followers"),
        following_count=p.get("following"),
        is_verified=p.get("verified", False),
        source="devtools",
        raw_data=p,
    )


def _parse_twitter_time(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%a %b %d %H:%M:%S %z %Y"]:
        try:
            return datetime.strptime(ts, fmt)
        except (ValueError, TypeError):
            continue
    return None


_EXTRACT_TWEETS_JS = """
(() => {
    const articles = document.querySelectorAll('article[data-testid="tweet"]');
    const results = [];
    const seen = new Set();
    for (const article of articles) {
        const link = article.querySelector('a[href*="/status/"]');
        if (!link) continue;
        const href = link.getAttribute('href') || '';
        const parts = href.split('/status/');
        const tweetId = parts.length > 1 ? parts[1].split('?')[0] : null;
        if (!tweetId || seen.has(tweetId)) continue;
        seen.add(tweetId);
        const usernameEl = article.querySelector('[data-testid="User-Name"] a');
        const username = usernameEl ? usernameEl.getAttribute('href')?.replace('/', '') || '' : '';
        const displayEl = article.querySelector('[data-testid="User-Name"] span');
        const displayName = displayEl ? displayEl.textContent || '' : '';
        const textEl = article.querySelector('[data-testid="tweetText"]');
        const text = textEl ? textEl.textContent || '' : '';
        const timeEl = article.querySelector('time');
        const timestamp = timeEl ? timeEl.getAttribute('datetime') || '' : '';
        const avatarEl = article.querySelector('img[alt*="photo"]');
        const avatarUrl = avatarEl ? avatarEl.getAttribute('src') || '' : '';
        const verified = !!article.querySelector('[data-testid="icon-verified"]');
        results.push({
            tweetId, username, displayName, text, timestamp, avatarUrl, verified
        });
    }
    return results;
})();
"""


_EXTRACT_PROFILE_JS = """
(() => {
    const dataEl = document.querySelector('script[type="application/ld+json"]');
    if (dataEl) {
        try {
            const data = JSON.parse(dataEl.textContent || '{}');
            const mainEntity = Array.isArray(data) ? data[0] : data;
            if (mainEntity && mainEntity['@type'] === 'Person') {
                return {
                    userId: mainEntity.identifier || '',
                    username: (mainEntity.alternateName || '').replace('@', ''),
                    displayName: mainEntity.name || '',
                    bio: mainEntity.description || '',
                    avatarUrl: (mainEntity.image || '').toString(),
                    followers: null,
                    following: null,
                    verified: false,
                };
            }
        } catch(e) {}
    }
    const lines = (document.querySelector('main')?.innerText || '').split('\\n').filter(l => l.trim());
    let displayName = '', username = '', bio = '', followers = null;
    for (let i = 0; i < lines.length; i++) {
        if (lines[i].startsWith('@') && !lines[i].includes(' ')) {
            username = lines[i];
            displayName = i > 0 ? lines[i-1] : '';
            let bioParts = [];
            for (let j = i + 1; j < lines.length; j++) {
                if (/^\\d+$/.test(lines[j]) || lines[j] === 'Following' || lines[j] === 'Followers') break;
                bioParts.push(lines[j]);
            }
            bio = bioParts.join(' ').trim();
        }
    }
    for (let i = 0; i < lines.length; i++) {
        if (lines[i] === 'Followers' && i > 0) {
            const n = parseInt(lines[i-1].replace(/[^0-9]/g, ''));
            if (!isNaN(n)) followers = n;
        }
    }
    const avatar = document.querySelector('img[alt="user avatar"]');
    const avatarUrl = avatar ? avatar.getAttribute('src') || '' : '';
    return {
        userId: username,
        username: username.replace('@', ''),
        displayName, bio, avatarUrl, followers,
        following: null, verified: false,
    };
})();
"""


import asyncio
