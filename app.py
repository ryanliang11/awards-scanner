import streamlit as st
import asyncio
from datetime import datetime, timedelta
import sys
from pathlib import Path
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))

from scanner.news_fetcher import NewsFetcher
from scanner.keyword_filter import KeywordFilter
from scanner.dedup import Deduplicator
import config

st.set_page_config(page_title="IT运维奖项扫描", page_icon="🏆", layout="wide")

st.title("🏆 IT运维奖项扫描智能体")
st.markdown("**AIOps | 智能运维 | 行业奖项 | 能力认证**")

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
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("DELETE FROM news WHERE created_at < ?", (cutoff,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

def get_news(limit=100, language=None, category=None, keyword=None):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = "SELECT * FROM news WHERE 1=1"
    params = []
    
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
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM news")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM news WHERE language = 'en'")
    en = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM news WHERE language = 'zh'")
    zh = c.fetchone()[0]
    conn.close()
    return {"total": total, "en": en, "zh": zh}

def run_scan():
    clean_old_news(days=7)
    
    existing_hashes = get_existing_hashes()
    
    fetcher = NewsFetcher()
    filter_obj = KeywordFilter()
    dedup = Deduplicator()
    dedup.load_from_db(existing_hashes)
    
    all_news = []
    
    with st.status("正在抓取英文新闻..."):
        try:
            en_news = asyncio.run(fetcher.fetch_news())
            all_news.extend(en_news)
            st.write(f"英文: {len(en_news)} 条")
        except Exception as e:
            st.write(f"英文抓取错误: {e}")
    
    with st.status("正在抓取中文新闻..."):
        try:
            zh_news = asyncio.run(fetcher.fetch_chinese_news())
            all_news.extend(zh_news)
            st.write(f"中文: {len(zh_news)} 条")
        except Exception as e:
            st.write(f"中文抓取错误: {e}")
    
    st.write(f"总计抓取: {len(all_news)} 条")
    
    filtered = filter_obj.filter(all_news)
    unique = dedup.deduplicate(filtered, days_filter=7)
    
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    en_count = 0
    zh_count = 0
    count = 0
    for item in unique:
        item["category"] = filter_obj.categorize(item)
        item["relevance"] = filter_obj.relevance_score(item)
        lang = item.get("language", "en")
        c.execute("""
            INSERT INTO news (title, url, snippet, published_at, keyword, source, language, category, relevance, scanned_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item.get("title"), item.get("url"), item.get("snippet"), 
              str(item.get("published_at")), item.get("keyword"),
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
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d")
    except:
        return str(date_str)[:10]

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
col1.metric("总新闻数", stats["total"])
col2.metric("🌐 英文", stats["en"])
col3.metric("🇨🇳 中文", stats["zh"])
if col4.button("🔄 手动扫描"):
    with st.spinner("扫描中，请稍候..."):
        try:
            count, en_count, zh_count = run_scan()
            st.success(f"扫描完成！新增 {count} 条 (英文:{en_count}, 中文:{zh_count})")
        except Exception as e:
            st.error(f"扫描出错: {e}")
        st.rerun()

st.divider()

col_search, col_lang, col_cat = st.columns([2, 1, 1])
keyword = col_search.text_input("🔍 搜索关键词", placeholder="输入关键词搜索...")
language = col_lang.selectbox("🌐 语言", ["全部", "en", "zh"], format_func=lambda x: {"全部": "全部", "en": "英文", "zh": "中文"}[x])
category = col_cat.selectbox("📂 分类", ["全部", "奖项启动", "获奖名单", "能力认证", "行业报告", "其他"])

news = get_news(100, language=language, category=category, keyword=keyword)

st.write(f"**共 {len(news)} 条结果**")

if not news:
    st.info("暂无新闻，点击上方「手动扫描」按钮抓取最新新闻！")
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
st.caption("🏆 IT运维奖项扫描智能体 | 扫描关键词: AIOps, 智能运维, Gartner, Forrester, 信通院, DevOps, SRE 等 | 自动过滤7天内重复新闻")
