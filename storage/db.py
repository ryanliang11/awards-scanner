import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import config

class Storage:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                snippet TEXT,
                published_at TEXT,
                keyword TEXT,
                source TEXT,
                language TEXT,
                category TEXT,
                relevance REAL DEFAULT 0,
                scanned_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_time TEXT,
                news_count INTEGER,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_published 
            ON news(published_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_category 
            ON news(category)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_news_language 
            ON news(language)
        """)
        
        conn.commit()
        conn.close()
    
    def save_news(self, news: Dict) -> int:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        published_at = news.get("published_at")
        if hasattr(published_at, "isoformat"):
            published_at = published_at.isoformat()
        
        scanned_at = news.get("scanned_at")
        if hasattr(scanned_at, "isoformat"):
            scanned_at = scanned_at.isoformat()
        
        cursor.execute("""
            INSERT INTO news (
                title, url, snippet, published_at, keyword, 
                source, language, category, relevance, scanned_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            news.get("title"),
            news.get("url"),
            news.get("snippet"),
            published_at,
            news.get("keyword"),
            news.get("source"),
            news.get("language"),
            news.get("category"),
            news.get("relevance", 0),
            scanned_at
        ))
        
        news_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return news_id
    
    def get_news(
        self, 
        limit: int = 50, 
        offset: int = 0,
        category: str = None,
        language: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM news WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if language:
            query += " AND language = ?"
            params.append(language)
        
        if start_date:
            query += " AND published_at >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND published_at <= ?"
            params.append(end_date)
        
        query += " ORDER BY published_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def search_news(self, keyword: str, limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_pattern = f"%{keyword}%"
        
        cursor.execute("""
            SELECT * FROM news 
            WHERE title LIKE ? OR snippet LIKE ? OR keyword LIKE ?
            ORDER BY published_at DESC
            LIMIT ?
        """, (search_pattern, search_pattern, search_pattern, limit))
        
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_hashes(self) -> List[str]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT title || '|' || url || '|' || source as hash
            FROM news
        """)
        
        rows = cursor.fetchall()
        
        conn.close()
        
        return [row[0] for row in rows]
    
    def save_scan_history(self, scan_time: datetime, count: int, status: str):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scan_history (scan_time, news_count, status)
            VALUES (?, ?, ?)
        """, (scan_time.isoformat(), count, status))
        
        conn.commit()
        conn.close()
    
    def get_scan_history(self, limit: int = 30) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM scan_history
            ORDER BY scan_time DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_statistics(self) -> Dict:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM news")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM news WHERE language = 'en'")
        en_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM news WHERE language = 'zh'")
        zh_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM news 
            GROUP BY category
        """)
        category_stats = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(*) FROM scan_history")
        scan_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_news": total,
            "english_count": en_count,
            "chinese_count": zh_count,
            "category_stats": category_stats,
            "total_scans": scan_count
        }
    
    def delete_old_news(self, days: int = 90):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM news 
            WHERE created_at < datetime('now', '-' || ? || ' days')
        """, (days,))
        
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted
