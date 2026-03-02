from typing import List, Dict, Set
import hashlib
from datetime import datetime, timedelta

class Deduplicator:
    def __init__(self, seen_hashes: Set[str] = None):
        self.seen_hashes = seen_hashes or set()
        
    def deduplicate(self, news_list: List[Dict]) -> List[Dict]:
        unique = []
        new_hashes = set()
        
        for item in news_list:
            content_hash = self._generate_hash(item)
            
            if content_hash not in self.seen_hashes and content_hash not in new_hashes:
                unique.append(item)
                new_hashes.add(content_hash)
        
        self.seen_hashes.update(new_hashes)
        
        return unique
    
    def _generate_hash(self, item: Dict) -> str:
        title = item.get("title", "")
        url = item.get("url", "")
        source = item.get("source", "")
        
        content = f"{title}|{url}|{source}"
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_duplicate(self, item: Dict) -> bool:
        content_hash = self._generate_hash(item)
        return content_hash in self.seen_hashes
    
    def mark_as_seen(self, item: Dict):
        content_hash = self._generate_hash(item)
        self.seen_hashes.add(content_hash)
    
    def load_from_db(self, hashes: List[str]):
        self.seen_hashes = set(hashes)
    
    def filter_recent(self, news_list: List[Dict], days: int = 7) -> List[Dict]:
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = []
        for item in news_list:
            published_at = item.get("published_at")
            if isinstance(published_at, datetime):
                if published_at >= cutoff:
                    recent.append(item)
            else:
                recent.append(item)
        
        return recent
