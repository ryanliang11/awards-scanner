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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        self.timeout = 10
        self.cutoff_date = datetime.now() - timedelta(days=7)
        
    async def fetch_news(self) -> List[Dict]:
        all_news = []
        
        search_queries = self._build_english_queries()
        
        for query in search_queries:
            try:
                news_items = await self._search_bing_en(query)
                all_news.extend(news_items)
                await asyncio.sleep(0.3)
            except Exception as e:
                continue
        
        return self._deduplicate(all_news)
    
    async def fetch_chinese_news(self) -> List[Dict]:
        all_news = []
        
        all_news.extend(await self._search_bing_chinese())
        
        return self._deduplicate(all_news)
    
    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        if not url:
            return None
        
        patterns = [
            r'/(\d{4})(\d{2})(\d{2})/',
            r'-(\d{4})(\d{2})(\d{2})',
            r'/(\d{8})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if groups[0] and len(groups[0]) == 4:
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:
                            continue
                    elif len(groups) == 1 and len(groups[0]) == 8:
                        year = int(groups[0][:4])
                        month = int(groups[0][4:6])
                        day = int(groups[0][6:8])
                    else:
                        continue
                    
                    if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day)
                except:
                    pass
        
        return None
    
    async def _extract_date_from_page(self, url: str) -> Optional[datetime]:
        try:
            async with httpx.AsyncClient(timeout=5, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
            
            if response.status_code != 200:
                return None
            
            html = response.text.lower()
            
            date_patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{4})/(\d{1,2})/(\d{1,2})',
                r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',
                r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s+(\d{4})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    try:
                        groups = match.groups()
                        if len(groups) == 3:
                            if groups[0].isdigit():
                                if len(groups[0]) == 4:
                                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                                else:
                                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                            else:
                                month_names = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
                                month = month_names.get(groups[0][:3].lower(), 1)
                                year = int(groups[2])
                                day = int(groups[1])
                            
                            if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                                return datetime(year, month, day)
                    except:
                        pass
        except:
            pass
        
        return None
    
    def _build_english_queries(self) -> List[Dict]:
        queries = []
        news_types = ["award", "winners", "certification", "recognition"]
        
        keywords = ["AIOps", "Intelligent Operations", "DevOps", "SRE", "Gartner", "Forrester"]
        
        for keyword in keywords:
            for news_type in news_types:
                queries.append({
                    "keyword": keyword,
                    "type": news_type,
                    "query": f"{keyword} {news_type}"
                })
        
        return queries[:15]
    
    async def _search_bing_chinese(self) -> List[Dict]:
        queries = [
            "AIOps 奖项 获奖",
            "智能运维 获奖 认证",
            "DevOps 认证 评选",
            "SRE 行业 奖项",
            "Gartner 中国 入选",
            "Forrester 报告 厂商",
            "site:weixin.qq.com AIOps 智能运维",
            "site:weixin.qq.com DevOps SRE",
            "微信公众号 AIOps 奖项",
            "微信公众号 智能运维 获奖",
        ]
        
        all_items = []
        
        for query in queries:
            try:
                url = f"https://www.bing.com/news/search?q={query}&setlang=zh-CN&count=50"
                
                async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                    response = await client.get(url)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, "html.parser")
                
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
                        
                        date_from_url = self._extract_date_from_url(url)
                        
                        if title and len(title) > 5:
                            page_date = await self._extract_date_from_page(url) if not date_from_url else date_from_url
                            if not page_date:
                                continue
                            
                            all_items.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet,
                                "published_at": page_date,
                                "keyword": query.split()[0],
                                "source": self._extract_source(url),
                                "language": "zh"
                            })
                    except Exception:
                        continue
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                continue
        
        return all_items
    
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
                    
                    date_from_url = self._extract_date_from_url(url)
                    
                    page_date = await self._extract_date_from_page(url) if not date_from_url else date_from_url
                    if not page_date:
                        continue
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": page_date,
                        "keyword": keyword,
                        "source": self._extract_source(url),
                        "language": "en"
                    })
                except Exception:
                    continue
            
            return news_items
            
        except Exception as e:
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
