from typing import List, Dict, Set
import hashlib
from datetime import datetime, timedelta

class Deduplicator:
    def __init__(self, seen_hashes: Set[str] = None):
        self.seen_hashes = seen_hashes or set()
        
    def deduplicate(self, news_list: List[Dict], days_filter: int = 7) -> List[Dict]:
        unique = []
        new_hashes = set()
        
        now = datetime.now()
        cutoff = now - timedelta(days=days_filter)
        
        for item in news_list:
            content_hash = self._generate_hash(item)
            
            if content_hash in new_hashes:
                continue
            
            if content_hash in self.seen_hashes:
                continue
            
            published_at = item.get("published_at")
            if published_at:
                try:
                    if isinstance(published_at, str):
                        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    else:
                        pub_date = published_at
                    
                    if pub_date >= cutoff:
                        pass
                except:
                    pass
            
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
        hash_set = set()
        for h in hashes:
            if h:
                try:
                    parts = h.split('|')
                    if len(parts) >= 3:
                        content = f"{parts[0]}|{parts[1]}|{parts[2]}"
                        hash_set.add(hashlib.md5(content.encode()).hexdigest())
                except:
                    pass
        self.seen_hashes = hash_set
    
    def filter_recent(self, news_list: List[Dict], days: int = 7) -> List[Dict]:
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = []
        for item in news_list:
            published_at = item.get("published_at")
            if isinstance(published_at, str):
                try:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    if pub_date >= cutoff:
                        recent.append(item)
                    else:
                        continue
                except:
                    recent.append(item)
            else:
                recent.append(item)
        
        return recent
