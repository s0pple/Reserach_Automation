from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source_type: str = "web_article"
    score: float = 0.5

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        pass

class DuckDuckGoSearchProvider(SearchProvider):
    """Real search using duckduckgo-search library."""
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(SearchResult(
                        title=r['title'],
                        url=r['href'],
                        snippet=r['body'],
                        score=0.8
                    ))
            return results
        except ImportError:
            print("⚠️ duckduckgo-search not found. Falling back to Mock.")
            return await MockSearchProvider().search(query, max_results)

class MockSearchProvider(SearchProvider):
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        return [SearchResult(f"Mock for {query}", "https://example.com", "Result text.")]
