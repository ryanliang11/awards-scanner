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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.timeout = 30
        
    async def fetch_news(self) -> List[Dict]:
        all_news = []
        
        search_queries = self._build_english_queries()
        
        for query in search_queries:
            try:
                news_items = await self._search_bing_en(query)
                all_news.extend(news_items)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Search error for {query}: {e}")
                continue
        
        return self._deduplicate(all_news)
    
    async def fetch_chinese_news(self) -> List[Dict]:
        all_news = []
        
        search_queries = self._build_chinese_queries()
        
        for query in search_queries:
            try:
                news_items = await self._search_baidu(query)
                all_news.extend(news_items)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Search error for {query}: {e}")
                continue
        
        if not all_news:
            try:
                news_items = await self._search_bing_zh()
                all_news.extend(news_items)
            except Exception as e:
                print(f"Bing ZH search error: {e}")
        
        return self._deduplicate(all_news)
    
    def _build_english_queries(self) -> List[Dict]:
        queries = []
        news_types = ["award", "winners", "certification", "recognition", "2024", "2025"]
        
        keywords = ["AIOps", "Intelligent Operations", "AI Operations", "DevOps", "SRE", 
                   "Site Reliability Engineering", "IT Operations", "Gartner", "Forrester",
                   "ITOM", "digital operations", "intelligent automation"]
        
        for keyword in keywords[:15]:
            for news_type in news_types[:4]:
                queries.append({
                    "keyword": keyword,
                    "type": news_type,
                    "query": f"{keyword} {news_type}"
                })
        
        return queries[:30]
    
    def _build_chinese_queries(self) -> List[Dict]:
        queries = []
        news_types = ["奖项", "获奖", "认证", "评选", "启动", "公布", "2024", "2025"]
        
        keywords = ["AIOps", "智能运维", "应用系统运维", "IT运维", "DevOps", "SRE",
                   "Gartner", "Forrester", "信通院", "IDC", "金融运维", "运营商运维",
                   "数字化运维", "IT运维奖项", "智能运维奖项", "行业奖项"]
        
        for keyword in keywords:
            for news_type in news_types:
                queries.append({
                    "keyword": keyword,
                    "type": news_type,
                    "query": f"{keyword} {news_type}"
                })
        
        return queries[:40]
    
    async def _search_bing_en(self, search_info: Dict) -> List[Dict]:
        query = search_info["query"]
        keyword = search_info["keyword"]
        
        url = f"https://www.bing.com/news/search?q={query}&setlang=en&count=50"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
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
                    
                    if not url or url.startswith("/"):
                        continue
                    
                    snippet_elem = article.select_one("div.snippet")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": datetime.now(),
                        "keyword": keyword,
                        "source": self._extract_source(url),
                        "language": "en"
                    })
                except Exception:
                    continue
            
            return news_items
            
        except Exception as e:
            print(f"Bing EN search failed: {e}")
            return []
    
    async def _search_bing_zh(self) -> List[Dict]:
        url = "https://www.bing.com/news/search?q=AIOps+%E5%A5%96%E5%A5%96&setlang=zh-CN"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
            
            soup = BeautifulSoup(response.text, "html.parser")
            news_items = []
            
            for article in soup.select("div.news-card"):
                try:
                    title_elem = article.select_one("a.title")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    
                    if not url or url.startswith("/"):
                        continue
                    
                    snippet_elem = article.select_one("div.snippet")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": datetime.now(),
                        "keyword": "AIOps",
                        "source": self._extract_source(url),
                        "language": "zh"
                    })
                except Exception:
                    continue
            
            return news_items
            
        except Exception as e:
            print(f"Bing ZH search failed: {e}")
            return []
    
    async def _search_baidu(self, search_info: Dict) -> List[Dict]:
        query = search_info["query"]
        keyword = search_info["keyword"]
        
        url = f"https://www.baidu.com/s?wd={query}&tn=news&rn=20"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
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
                    
                    if "localhost" in url or url.startswith("/") or not url:
                        continue
                    
                    snippet_elem = result.select_one("div.c-abstract")
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    if len(snippet) > 10:
                        news_items.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet[:200],
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
            title_short = item.get("title", "")[:30]
            key = (title_short, item.get("source", ""))
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique
