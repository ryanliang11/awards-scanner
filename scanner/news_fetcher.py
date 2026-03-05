import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import config
from tavily import TavilyClient

class NewsFetcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        self.timeout = 10
        self.cutoff_date = datetime.now() - timedelta(days=7)
        self.tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
    async def fetch_news(self) -> List[Dict]:
        all_news = []
        
        search_queries = self._build_english_queries()
        
        for query in search_queries:
            try:
                news_items = await self._search_tavily(query)
                all_news.extend(news_items)
                await asyncio.sleep(0.5)
            except Exception as e:
                continue
        
        return self._deduplicate(all_news)
    
    async def fetch_chinese_news(self) -> List[Dict]:
        all_news = []
        
        chinese_queries = [
            "AIOps 奖 申报", "AIOps 奖 申请", "AIOps 奖 评选",
            "AIOps 认证 申报", "AIOps 认证 申请", "AIOps 认证 评选",
            "智能运维 奖 申报", "智能运维 奖 申请", "智能运维 奖 评选",
            "智能运维 认证 申报", "智能运维 认证 申请", "智能运维 认证 评选",
            "DevOps 奖 申报", "DevOps 奖 申请", "DevOps 奖 评选",
            "DevOps 认证 申报", "DevOps 认证 申请", "DevOps 认证 评选",
            "AI 奖 申报", "AI 奖 申请", "AI 奖 评选",
            "AI 认证 申报", "AI 认证 申请", "AI 认证 评选",
            "智能体 奖 申报", "智能体 奖 申请", "智能体 奖 评选",
            "智能体 认证 申报", "智能体 认证 申请", "智能体 认证 评选",
        ]
        
        for query in chinese_queries:
            try:
                news_items = await self._search_tavily({"query": query, "keyword": query.split()[0]}, language="zh")
                all_news.extend(news_items)
                await asyncio.sleep(0.5)
            except Exception as e:
                continue
        
        return self._deduplicate(all_news)
    
    async def _search_tavily(self, search_info: Dict, language: str = "en") -> List[Dict]:
        query = search_info["query"]
        keyword = search_info["keyword"]
        
        try:
            response = self.tavily_client.search(
                query=f"{query}",
                max_results=10,
                time_range="week"
            )
            
            news_items = []
            
            for item in response.get("results", []):
                try:
                    url = item.get("url", "")
                    if not url:
                        continue
                    
                    title = item.get("title", "")
                    snippet = item.get("content", "")
                    
                    date_from_url = self._extract_date_from_url(url)
                    
                    page_date = await self._extract_date_from_page(url) if not date_from_url else date_from_url
                    if not page_date:
                        continue
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet[:200] if snippet else "",
                        "published_at": page_date,
                        "keyword": keyword,
                        "source": self._extract_source(url),
                        "language": language
                    })
                except Exception:
                    continue
            
            return news_items
            
        except Exception as e:
            return []
    
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
        news_types = ["award", "certification", "apply", "application", "selection", "winners", "conference", "summit"]
        
        keywords = ["AIOps", "Intelligent Operations", "DevOps", "AI", "Agent"]
        
        for keyword in keywords:
            for news_type in news_types:
                queries.append({
                    "keyword": keyword,
                    "type": news_type,
                    "query": f"{keyword} {news_type}"
                })
        
        return queries[:20]
    
    async def _search_bing_chinese(self) -> List[Dict]:
        queries = [
            "AIOps 奖项 获奖",
            "智能运维 获奖 认证",
            "IT运维 奖项 获奖",
            "云原生 奖项 评选",
            "可观测性 奖项 峰会",
            "监控 获奖 认证",
            "运维自动化 奖项",
            "DevOps 认证 评选",
            "SRE 行业 奖项",
            "Gartner 中国 入选",
            "Forrester 报告 厂商",
            "AIOps 峰会 大会",
            "智能运维 峰会 评选",
            "AI 运维 奖项 获奖",
            "AI 智能体 奖项 认证",
            "Agent 智能体 奖项 评选",
            "智能体 运维 获奖",
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
    
    async def _search_google_en(self, search_info: Dict) -> List[Dict]:
        query = search_info["query"]
        keyword = search_info["keyword"]
        
        url = f"https://news.google.com/search?q={query}&hl=en-US"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            news_items = []
            
            for article in soup.select("article"):
                try:
                    title_elem = article.select_one("a.MBeuO")
                    if not title_elem:
                        title_elem = article.select_one("a")
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    
                    if not href or not href.startswith("http"):
                        continue
                    
                    url = href
                    
                    snippet_elem = article.select_one("div.SoaBEf")
                    snippet = ""
                    if snippet_elem:
                        snippet_elem2 = snippet_elem.select_one("div.MbOVd")
                        if snippet_elem2:
                            snippet = snippet_elem2.get_text(strip=True)
                    
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
