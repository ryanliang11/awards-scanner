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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.timeout = 15
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
        
        all_news.extend(await self._search_baidu_tech())
        
        if not all_news:
            all_news.extend(await self._search_bing_chinese_v2())
        
        return self._deduplicate(all_news)
    
    async def _fetch_article_date(self, url: str) -> Optional[datetime]:
        if not url or url.startswith("/") or "localhost" in url:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url)
                
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            date_patterns = [
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{4})/(\d{1,2})/(\d{1,2})',
                r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            ]
            
            text = soup.get_text()
            
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        if 2000 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                            return datetime(year, month, day)
                    except:
                        pass
            
            time_patterns = [
                r'time["\s:]+(\d{4})-(\d{1,2})-(\d{1,2})',
                r'publishDate["\s:]+(\d{4})-(\d{1,2})-(\d{1,2})',
                r'datePublished["\s:]+(\d{4})-(\d{1,2})-(\d{1,2})',
                r'<time[^>]*>(\d{4})-(\d{1,2})-(\d{1,2})',
            ]
            
            html = response.text
            for pattern in time_patterns:
                match = re.search(pattern, html)
                if match:
                    try:
                        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                        if 2000 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                            return datetime(year, month, day)
                    except:
                        pass
            
            return None
            
        except:
            return None
    
    async def _process_news_with_date(self, news_list: List[Dict]) -> List[Dict]:
        result = []
        
        for item in news_list:
            pub_date = await self._fetch_article_date(item.get("url", ""))
            if pub_date:
                item["published_at"] = pub_date
            else:
                url_date = self._extract_date_from_url(item.get("url", ""))
                if url_date:
                    item["published_at"] = url_date
                else:
                    item["published_at"] = datetime.now()
            
            if item["published_at"] >= self.cutoff_date:
                result.append(item)
        
        return result
    
    def _extract_date_from_url(self, url: str) -> Optional[datetime]:
        if not url:
            return None
        
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})_(\d{1,2})_(\d{1,2})',
            r'/(\d{4})(\d{2})(\d{2})/',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, url)
            if match:
                try:
                    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if 2000 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        return datetime(year, month, day)
                except:
                    pass
        
        return None
    
    def _build_english_queries(self) -> List[Dict]:
        queries = []
        news_types = ["award", "winners", "certification", "2025", "2026"]
        
        keywords = ["AIOps", "Intelligent Operations", "AI Operations", "DevOps", "SRE", 
                   "Site Reliability Engineering", "IT Operations", "Gartner", "Forrester",
                   "ITOM", "digital operations"]
        
        for keyword in keywords[:12]:
            for news_type in news_types[:3]:
                queries.append({
                    "keyword": keyword,
                    "type": news_type,
                    "query": f"{keyword} {news_type}"
                })
        
        return queries[:25]
    
    async def _search_bing_chinese(self) -> List[Dict]:
        queries = [
            "AIOps 奖项 2025",
            "智能运维 获奖", 
            "DevOps 认证",
            "SRE 行业奖项",
            "信通院 评估",
            "Gartner 中国",
            "Forrester 中国",
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
                        
                        if title and len(title) > 5:
                            all_items.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet,
                                "published_at": None,
                                "keyword": query.split()[0],
                                "source": self._extract_source(url),
                                "language": "zh"
                            })
                    except Exception:
                        continue
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                continue
        
        return await self._process_news_with_date(all_items)
    
    async def _search_bing_chinese_v2(self) -> List[Dict]:
        keywords = ["智能运维", "AIOps", "DevOps", "SRE"]
        
        all_items = []
        
        for kw in keywords:
            try:
                url = f"https://cn.bing.com/news/search?q={kw}%20%E5%A5%96&setlang=zh-CN"
                
                async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                    response = await client.get(url)
                
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
                        
                        all_items.append({
                            "title": title,
                            "url": url,
                            "snippet": "",
                            "published_at": None,
                            "keyword": kw,
                            "source": self._extract_source(url),
                            "language": "zh"
                        })
                    except Exception:
                        continue
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                continue
        
        return await self._process_news_with_date(all_items)
    
    async def _search_baidu_tech(self) -> List[Dict]:
        queries = [
            "智能运维 奖项 2025",
            "AIOps 获奖",
            "DevOps 认证",
            "SRE 行业",
        ]
        
        all_items = []
        
        for query in queries:
            try:
                encoded_query = query.replace(" ", "+")
                url = f"https://www.baidu.com/s?wd={encoded_query}&tn=news&rn=20"
                
                async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                    response = await client.get(url)
                
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                for result in soup.select("div.result"):
                    try:
                        title_elem = result.select_one("h3.t a")
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get("href", "")
                        
                        if "localhost" in url or url.startswith("/") or not url or "baidu.com" in url:
                            continue
                        
                        snippet_elem = result.select_one("div.c-abstract")
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                        
                        if title and len(title) > 5:
                            all_items.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet[:200] if snippet else "",
                                "published_at": None,
                                "keyword": query.split()[0],
                                "source": self._extract_source(url),
                                "language": "zh"
                            })
                    except Exception:
                        continue
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                continue
        
        return await self._process_news_with_date(all_items)
    
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
                        "published_at": None,
                        "keyword": keyword,
                        "source": self._extract_source(url),
                        "language": "en"
                    })
                except Exception:
                    continue
            
            return await self._process_news_with_date(news_items)
            
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
