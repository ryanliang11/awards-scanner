import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import config

class NewsFetcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.timeout = 30
        
    async def fetch_news(self) -> List[Dict]:
        all_news = []
        
        search_queries = self._build_search_queries()
        
        for query in search_queries:
            try:
                news_items = await self._search_bing(query)
                all_news.extend(news_items)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Search error for {query}: {e}")
                continue
        
        return self._deduplicate(all_news)
    
    def _build_search_queries(self) -> List[Dict]:
        queries = []
        news_types = ["奖项启动", "获奖名单", "能力认证", "winners", "award", "certification"]
        
        for keyword in config.KEYWORDS:
            for news_type in news_types:
                queries.append({
                    "keyword": keyword,
                    "type": news_type,
                    "query": f"{keyword} {news_type}"
                })
        
        return queries[:50]
    
    async def _search_bing(self, search_info: Dict) -> List[Dict]:
        query = search_info["query"]
        keyword = search_info["keyword"]
        
        url = f"https://www.bing.com/news/search?q={query}&setlang=en&count=50"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url)
                
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            news_items = []
            
            for article in soup.select("div.news-card"):
                try:
                    title_elem = article.select_one("a.title")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    
                    snippet_elem = article.select_one("div.snippet")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    date_elem = article.select_one("span.news-date")
                    date_str = date_elem.get_text(strip=True) if date_elem else ""
                    
                    published_at = self._parse_date(date_str)
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": published_at,
                        "keyword": keyword,
                        "source": self._extract_source(url),
                        "language": "en"
                    })
                except Exception:
                    continue
            
            return news_items
            
        except Exception as e:
            print(f"Bing search failed: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return datetime.now()
        
        date_str = date_str.lower()
        
        now = datetime.now()
        
        if "hour" in date_str or "minute" in date_str:
            return now
        elif "day" in date_str:
            match = re.search(r"(\d+)", date_str)
            if match:
                days = int(match.group(1))
                return now - timedelta(days=days)
        elif "week" in date_str:
            match = re.search(r"(\d+)", date_str)
            if match:
                weeks = int(match.group(1))
                return now - timedelta(weeks=weeks)
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return now
    
    def _extract_source(self, url: str) -> str:
        if not url:
            return "unknown"
        
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        if match:
            return match.group(1)
        return "unknown"
    
    def _deduplicate(self, news_list: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        
        for item in news_list:
            key = (item.get("title", "")[:50], item.get("source", ""))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique
    
    async def fetch_chinese_news(self) -> List[Dict]:
        all_news = []
        search_queries = self._build_chinese_queries()
        
        for query in search_queries:
            try:
                news_items = await self._search_baidu(query)
                all_news.extend(news_items)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Search error for {query}: {e}")
                continue
        
        return self._deduplicate(all_news)
    
    def _build_chinese_queries(self) -> List[Dict]:
        queries = []
        news_types = ["奖项", "获奖", "认证", "评选", "启动", "公布"]
        
        chinese_keywords = [
            "AIOps", "智能运维", "应用系统运维", "智能体运维",
            "Gartner", "Forrester", "信通院", "IDC",
            "金融运维", "运营商运维", "IT运维"
        ]
        
        for keyword in chinese_keywords:
            for news_type in news_types:
                queries.append({
                    "keyword": keyword,
                    "type": news_type,
                    "query": f"{keyword} {news_type}"
                })
        
        return queries[:30]
    
    async def _search_baidu(self, search_info: Dict) -> List[Dict]:
        query = search_info["query"]
        keyword = search_info["keyword"]
        
        url = f"https://www.baidu.com/s?wd={query}&tn=news&rn=50"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(url)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            news_items = []
            
            for result in soup.select("div.result"):
                try:
                    title_elem = result.select_one("h3.t a")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    
                    if "localhost" in url or url.startswith("/"):
                        continue
                    
                    snippet_elem = result.select_one("div.c-abstract")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": datetime.now(),
                        "keyword": keyword,
                        "source": self._extract_source(url),
                        "language": "zh"
                    })
                except Exception:
                    continue
            
            return news_items
            
        except Exception as e:
            print(f"Baidu search failed: {e}")
            return []

async def main():
    fetcher = NewsFetcher()
    news = await fetcher.fetch_news()
    print(f"Found {len(news)} news items")

if __name__ == "__main__":
    asyncio.run(main())
