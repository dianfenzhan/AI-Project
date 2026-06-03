from typing import List, Dict, Any
from serpapi import GoogleSearch
import requests
from bs4 import BeautifulSoup
from RAG.config import Config as RAGConfig
from .config import Config


class SerpSearch:
    """通过 SerpAPI 检索 Google，并抓取正文，作为生成阶段的实时外部知识。"""

    def __init__(self):
        self.api_key = Config.SERP_API_KEY

    def search(self, query: str, num_results: int = None) -> List[Dict[str, Any]]:
        num_results = num_results or RAGConfig.TOP_K_SEARCH
        params = {
            "q": query,
            "api_key": self.api_key,
            "num": num_results,
            "hl": "zh-cn",
            "gl": "cn",
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        organic_results = results.get("organic_results", [])[:num_results]

        return [
            {
                "title": r.get("title"),
                "link": r.get("link"),
                "snippet": r.get("snippet"),
            }
            for r in organic_results
            if r.get("link")
        ]

    def fetch_page_content(self, url: str, max_chars: int = 5000) -> str:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; SEO-RAG-Bot/1.0)"}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            paragraphs = soup.find_all("p")
            content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            return content[:max_chars]
        except Exception as e:
            return f"[抓取失败 {url}: {e}]"

    def search_and_fetch(self, query: str, num_results: int = None) -> List[Dict[str, Any]]:
        """检索 + 抓取正文，返回带 content 的结果列表。"""
        results = self.search(query, num_results)
        for r in results:
            r["content"] = self.fetch_page_content(r["link"])
        return results
