import streamlit as st
import asyncio
from datetime import datetime, timedelta, date
import sys
from pathlib import Path
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))

from scanner.news_fetcher import NewsFetcher
from scanner.keyword_filter import KeywordFilter
from scanner.dedup import Deduplicator
import config

st.set_page_config(page_title="Awards Scanner", page_icon="🏆", layout="wide")

st.title("🏆 IT Operations Awards Scanner")
st.markdown("**AIOps | Intelligent Operations | DevOps | SRE**")

DB_PATH = Path(__file__).parent / "data" / "awards.db"

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_time TEXT,
            news_count INTEGER,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_existing_hashes():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT title, url, source FROM news")
    rows = c.fetchall()
    conn.close()
    return [f"{r[0]}|{r[1]}|{r[2]}" for r in rows]

def clean_old_news(days=7):
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("DELETE FROM news WHERE published_at < ?", (cutoff_str,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

def get_news(limit=100, language=None, category=None, keyword=None, start_date=None, end_date=None):
    effective_start = start_date if start_date else (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    effective_end = end_date if end_date else datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = "SELECT * FROM news WHERE published_at >= ? AND published_at <= ?"
    params = [effective_start, effective_end]
    
    if language and language != "全部":
        query += " AND language = ?"
        params.append(language)
    
    if category and category != "全部":
        query += " AND category = ?"
        params.append(category)
    
    if keyword:
        query += " AND (title LIKE ? OR snippet LIKE ? OR keyword LIKE ?)"
        search_term = f"%{keyword}%"
        params.extend([search_term, search_term, search_term])
    
    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    cutoff = datetime.now() - timedelta(days=7)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM news WHERE published_at >= ?", (cutoff_str,))
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM news WHERE language = 'en' AND published_at >= ?", (cutoff_str,))
    en = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM news WHERE language = 'zh' AND published_at >= ?", (cutoff_str,))
    zh = c.fetchone()[0]
    conn.close()
    return {"total": total, "en": en, "zh": zh}

def is_recent(pub_date) -> bool:
    if not pub_date:
        return False
    try:
        pub_str = str(pub_date)[:10]
        pub_dt = datetime.strptime(pub_str, "%Y-%m-%d")
        cutoff = datetime.now() - timedelta(days=7)
        return pub_dt >= cutoff
    except:
        return False

def run_scan(start_date=None, end_date=None):
    clean_old_news(days=7)
    
    existing_hashes = get_existing_hashes()
    
    fetcher = NewsFetcher(start_date=start_date, end_date=end_date)
    filter_obj = KeywordFilter()
    dedup = Deduplicator()
    dedup.load_from_db(existing_hashes)
    
    all_news = []
    
    with st.status("Fetching English news..."):
        try:
            en_news = asyncio.run(fetcher.fetch_news())
            all_news.extend(en_news)
            st.write(f"English: {len(en_news)}")
        except Exception as e:
            st.write(f"Error: {e}")
    
    with st.status("Fetching Chinese news..."):
        try:
            zh_news = asyncio.run(fetcher.fetch_chinese_news())
            all_news.extend(zh_news)
            st.write(f"Chinese: {len(zh_news)}")
        except Exception as e:
            st.write(f"Error: {e}")
    
    st.write(f"Total: {len(all_news)}")
    
    filtered = filter_obj.filter(all_news)
    unique = dedup.deduplicate(filtered, days_filter=7)
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    en_count = 0
    zh_count = 0
    count = 0
    for item in unique:
        if not is_recent(item.get("published_at")):
            continue
            
        item["category"] = filter_obj.categorize(item)
        item["relevance"] = filter_obj.relevance_score(item)
        lang = item.get("language", "en")
        
        pub_at = item.get("published_at")
        if hasattr(pub_at, "strftime"):
            pub_str = pub_at.strftime("%Y-%m-%d")
        else:
            pub_str = str(pub_at)[:10]
        
        c.execute("""
            INSERT INTO news (title, url, snippet, published_at, keyword, source, language, category, relevance, scanned_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item.get("title"), item.get("url"), item.get("snippet"), 
              pub_str, item.get("keyword"),
              item.get("source"), lang, item.get("category"),
              item.get("relevance", 0), datetime.now().isoformat()))
        count += 1
        if lang == "en":
            en_count += 1
        else:
            zh_count += 1
    
    c.execute("INSERT INTO scan_history (scan_time, news_count, status) VALUES (?, ?, ?)",
              (datetime.now().isoformat(), count, "success"))
    conn.commit()
    conn.close()
    return count, en_count, zh_count

def format_date(date_str):
    if not date_str:
        return "N/A"
    try:
        date_str = str(date_str)[:10]
        return date_str
    except:
        return "N/A"

def is_valid_date(date_str):
    if not date_str:
        return False
    try:
        date_str = str(date_str)[:10]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        now = datetime.now()
        cutoff = now - timedelta(days=7)
        return dt >= cutoff
    except:
        return False

def get_category_color(cat):
    colors = {
        "奖项启动": "#4CAF50",
        "获奖名单": "#2196F3", 
        "能力认证": "#FF9800",
        "行业报告": "#9C27B0",
        "其他": "#757575"
    }
    return colors.get(cat, "#757575")

init_db()

col1, col2, col3, col4 = st.columns(4)
stats = get_stats()
col1.metric("Total", stats["total"])
col2.metric("EN", stats["en"])
col3.metric("CN", stats["zh"])

col_scan1, col_scan2 = st.columns(2)
default_start_scan = (datetime.now() - timedelta(days=7)).date()
default_end_scan = datetime.now().date()
start_date_scan = col_scan1.date_input("Scan Start", value=default_start_scan)
end_date_scan = col_scan2.date_input("Scan End", value=default_end_scan)

if col4.button("Scan"):
    with st.spinner("Scanning..."):
        try:
            start_str = start_date_scan.strftime("%Y-%m-%d") if start_date_scan else None
            end_str = end_date_scan.strftime("%Y-%m-%d") if end_date_scan else None
            count, en_count, zh_count = run_scan(start_str, end_str)
            st.success(f"Done! New: {count} (EN:{en_count}, CN:{zh_count})")
        except Exception as e:
            st.error(f"Error: {e}")
        st.rerun()

st.divider()

col_search, col_lang = st.columns([2, 1])
keyword = col_search.text_input("Search", placeholder="Keyword...")
language = col_lang.selectbox("Lang", ["全部", "en", "zh"])

col_cat, col_date1, col_date2 = st.columns([1, 1, 1])
category = col_cat.selectbox("Category", ["全部", "奖项启动", "获奖名单", "能力认证", "行业报告", "其他"])

default_start = (datetime.now() - timedelta(days=7)).date()
default_end = datetime.now().date()
start_date = col_date1.date_input("Start", value=default_start)
end_date = col_date2.date_input("End", value=default_end)

start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None

news = get_news(100, language=language, category=category, keyword=keyword, start_date=start_date_str, end_date=end_date_str)

st.write(f"**{len(news)} results ({start_date_str} ~ {end_date_str})**")

if not news:
    st.info("No news. Click Scan button!")
else:
    for item in news:
        title = item.get('title', '')[:70]
        if len(item.get('title', '')) > 70:
            title += '...'
        
        cat = item.get('category', '其他')
        cat_color = get_category_color(cat)
        lang = 'CN' if item.get('language') == 'zh' else 'EN'
        date = format_date(item.get('published_at'))
        source = item.get('source', 'N/A')
        url = item.get('url', '#')
        
        with st.container():
            col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns([5, 1.5, 1, 1.5, 1])
            
            with col_t1:
                st.markdown(f"📰 [{title}]({url})")
            
            with col_t2:
                st.markdown(f"<span style='background-color:{cat_color};color:white;padding:2px 8px;border-radius:10px;font-size:12px;'>{cat}</span>", unsafe_allow_html=True)
            
            with col_t3:
                st.markdown(f"**{lang}**")
            
            with col_t4:
                st.markdown(f"📅 {date}")
            
            with col_t5:
                st.caption(source[:15])
            
            st.divider()

st.markdown("---")
st.caption("Awards Scanner | Filter: 7 days only | Keywords: AIOps, Intelligent Operations, DevOps, SRE, Gartner, Forrester")
