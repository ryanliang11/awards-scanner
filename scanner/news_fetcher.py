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
        self.timeout = 30
        self.cutoff_date = datetime.now() - timedelta(days=7)
        
    async def fetch_news(self) -> List[Dict]:
        all_news = []
        
        search_queries = self._build_english_queries()
        
        for query in search_queries:
            try:
                news_items = await self._search_bing_en(query)
                news_items = self._filter_by_date(news_items)
                all_news.extend(news_items)
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Search error for {query}: {e}")
                continue
        
        return self._deduplicate(all_news)
    
    async def fetch_chinese_news(self) -> List[Dict]:
        all_news = []
        
        all_news.extend(await self._search_bing_chinese())
        
        all_news.extend(await self._search_baidu_tech())
        
        if not all_news:
            all_news.extend(await self._search_bing_chinese_v2())
        
        all_news = self._filter_by_date(all_news)
        
        return self._deduplicate(all_news)
    
    def _filter_by_date(self, news_list: List[Dict]) -> List[Dict]:
        filtered = []
        for item in news_list:
            pub_date = item.get("published_at")
            if pub_date:
                try:
                    if isinstance(pub_date, str):
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    if pub_date >= self.cutoff_date:
                        filtered.append(item)
                except:
                    filtered.append(item)
            else:
                filtered.append(item)
        return filtered
    
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
    
    async def _search_bing_chinese(self) -> List[Dict]:
        queries = [
            "AIOps 奖项",
            "智能运维 获奖", 
            "DevOps 认证",
            "SRE 行业奖项",
            "信通院 评估",
            "Gartner 中国",
            "Forrester 中国",
            "IT运维 奖项 2024",
            "数字化运维 评选",
            "金融科技运维 认证"
        ]
        
        all_items = []
        
        for query in queries[:8]:
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
                        
                        date_str = self._extract_date_from_article(article)
                        
                        if title and len(title) > 5:
                            all_items.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet,
                                "published_at": date_str,
                                "keyword": query.split()[0],
                                "source": self._extract_source(url),
                                "language": "zh"
                            })
                    except Exception:
                        continue
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"Bing Chinese search error for {query}: {e}")
                continue
        
        return all_items
    
    async def _search_bing_chinese_v2(self) -> List[Dict]:
        keywords = ["智能运维", "AIOps", "DevOps", "SRE", "IT运维"]
        
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
                        
                        date_str = self._extract_date_from_article(article)
                        
                        all_items.append({
                            "title": title,
                            "url": url,
                            "snippet": "",
                            "published_at": date_str,
                            "keyword": kw,
                            "source": self._extract_source(url),
                            "language": "zh"
                        })
                    except Exception:
                        continue
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                continue
        
        return all_items
    
    async def _search_baidu_tech(self) -> List[Dict]:
        queries = [
            "智能运维 奖项 2024",
            "AIOps 获奖",
            "DevOps 认证 评测",
            "SRE 行业 评选",
            "IT运维 奖项"
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
                        
                        date_str = self._extract_date_from_baidu(result)
                        
                        if title and len(title) > 5:
                            all_items.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet[:200] if snippet else "",
                                "published_at": date_str,
                                "keyword": query.split()[0],
                                "source": self._extract_source(url),
                                "language": "zh"
                            })
                    except Exception:
                        continue
                
                await asyncio.sleep(0.3)
                
            except Exception as e:
                print(f"Baidu search error: {e}")
                continue
        
        return all_items
    
    def _extract_date_from_article(self, article) -> datetime:
        try:
            date_elem = article.select_one("span.news-date")
            if date_elem:
                date_text = date_elem.get_text(strip=True).lower()
                return self._parse_date_string(date_text)
        except:
            pass
        return datetime.now()
    
    def _extract_date_from_baidu(self, result) -> datetime:
        try:
            date_elem = result.select_one("span.c-info-color")
            if date_elem:
                date_text = date_elem.get_text(strip=True).lower()
                return self._parse_date_string(date_text)
        except:
            pass
        return datetime.now()
    
    def _parse_date_string(self, date_text: str) -> datetime:
        date_text = date_text.lower()
        now = datetime.now()
        
        if "小时" in date_text or "hour" in date_text:
            return now
        if "分钟" in date_text or "minute" in date_text:
            return now
        if "天" in date_text or "day" in date_text:
            match = re.search(r"(\d+)", date_text)
            if match:
                days = int(match.group(1))
                return now - timedelta(days=days)
        if "周" in date_text or "week" in date_text:
            match = re.search(r"(\d+)", date_text)
            if match:
                weeks = int(match.group(1))
                return now - timedelta(weeks=weeks)
        if "月" in date_text or "month" in date_text:
            match = re.search(r"(\d+)", date_text)
            if match:
                months = int(match.group(1))
                return now - timedelta(days=months*30)
        
        try:
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"]:
                return datetime.strptime(date_text[:10], fmt)
        except:
            pass
        
        return now
    
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
                    
                    date_str = self._extract_date_from_article(article)
                    
                    news_items.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "published_at": date_str,
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
