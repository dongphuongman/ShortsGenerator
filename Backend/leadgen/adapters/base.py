from abc import ABC, abstractmethod
from typing import Optional

from leadgen.schemas import Lead


class LeadSourceAdapter(ABC):
    @abstractmethod
    async def search_keyword(self, keyword: str, platform: str, max_results: int = 20) -> list[Lead]:
        ...

    @abstractmethod
    async def get_profile(self, username: str, platform: str) -> Optional[Lead]:
        ...

    @abstractmethod
    async def search_hashtag(self, hashtag: str, platform: str, max_results: int = 20) -> list[Lead]:
        ...

    @abstractmethod
    async def search_niche(self, seed_username: str, platform: str, max_results: int = 20) -> list[Lead]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
