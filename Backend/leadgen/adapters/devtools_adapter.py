from typing import Optional

from leadgen.schemas import Lead
from leadgen.adapters.base import LeadSourceAdapter
from leadgen.devtools.twitter import search_tweets, get_profile


class DevToolsAdapter(LeadSourceAdapter):
    def __init__(self, chrome_port: int = 9222):
        self.chrome_port = chrome_port

    async def search_keyword(self, keyword: str, platform: str, max_results: int = 20) -> list[Lead]:
        if platform == "twitter":
            return await search_tweets(keyword, max_results, self.chrome_port)
        raise ValueError(f"Platform '{platform}' not yet supported via DevTools adapter")

    async def get_profile(self, username: str, platform: str) -> Optional[Lead]:
        if platform == "twitter":
            return await get_profile(username, self.chrome_port)
        raise ValueError(f"Platform '{platform}' not yet supported via DevTools adapter")

    async def search_hashtag(self, hashtag: str, platform: str, max_results: int = 20) -> list[Lead]:
        return await self.search_keyword(hashtag, platform, max_results)

    async def search_niche(self, seed_username: str, platform: str, max_results: int = 20) -> list[Lead]:
        profile = await self.get_profile(seed_username, platform)
        if not profile:
            raise ValueError(f"Could not find profile '{seed_username}' on {platform}")
        return await self.search_keyword(seed_username, platform, max_results)

    async def health_check(self) -> bool:
        from leadgen.devtools.connector import ChromeConnector
        conn = ChromeConnector(port=self.chrome_port)
        result = await conn.connect()
        if result:
            await conn.disconnect()
        return result
