from typing import List, Dict
import re
import config

class KeywordFilter:
    def __init__(self):
        self.keywords = config.KEYWORDS
        self.news_types = config.NEWS_TYPES
        
    def filter(self, news_list: List[Dict]) -> List[Dict]:
        filtered = []
        
        for item in news_list:
            if self._matches_keywords(item):
                filtered.append(item)
        
        return filtered
    
    def _matches_keywords(self, item: Dict) -> bool:
        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        
        content = f"{title} {snippet}"
        
        for keyword in self.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in content:
                return True
        
        for news_type in self.news_types:
            news_type_lower = news_type.lower()
            if news_type_lower in content:
                return True
        
        return False
    
    def categorize(self, item: Dict) -> str:
        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        content = f"{title} {snippet}"
        
        categories = {
            "奖项启动": ["奖项启动", "award launch", "申报", "call for", "征集", "报名", "开始", "launch"],
            "获奖名单": ["获奖", "winners", "获奖名单", "award winners", "公布", "winner", "获奖者", "荣誉"],
            "能力认证": ["认证", "certification", "资质", "通过", "获得", "approved", "recognized"],
            "行业报告": ["报告", "report", "研究", "研究", "分析", "quadrant", "wave", "评估"]
        }
        
        for category, keywords in categories.items():
            for kw in keywords:
                if kw in content:
                    return category
        
        return "其他"
    
    def relevance_score(self, item: Dict) -> float:
        title = item.get("title", "").lower()
        snippet = item.get("snippet", "").lower()
        content = f"{title} {snippet}"
        
        score = 0
        
        core_keywords = ["aiops", "智能运维", "intelligent operations", "ai operations"]
        for kw in core_keywords:
            if kw in content:
                score += 10
        
        secondary_keywords = ["gartner", "forrester", "信通院", "devops", "sre"]
        for kw in secondary_keywords:
            if kw in content:
                score += 5
        
        award_keywords = ["award", "奖项", "获奖", "winners", "认证", "certification"]
        for kw in award_keywords:
            if kw in content:
                score += 3
        
        return score
