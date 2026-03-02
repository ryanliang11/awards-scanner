import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SCAN_TIME = "09:00"

KEYWORDS = [
    "AIOps", "智能运维", "AI Operations", "Intelligent Operations",
    "应用系统运维", "智能体运维", "AI-powered operations",
    "Gartner", "Forrester", "信通院", "IDC", "魔力象限", "Magic Quadrant", "Wave评估",
    "金融运维", "运营商运维", "电力运维", "政务运维", "金融科技运维",
    "DevOps World", "AIOps Global Summit", "KubeCon", "SREcon",
    "IT运维奖项", "operations award", "intelligent operations award",
    "SRE", "Site Reliability Engineering", "运维自动化",
    "ITOM", "IT Operations Management", "数字化运维"
]

NEWS_TYPES = [
    "奖项启动", "award launch", "奖项申报", "call for nominations",
    "获奖名单", "winners announced", "award winners", "获奖结果",
    "能力认证", "certification", "资质认证", "认证通过",
    "行业报告", "industry report", "评估报告", "magic quadrant"
]

LANGUAGES = ["en", "zh"]

DATABASE_PATH = DATA_DIR / "awards.db"

WEB_HOST = "0.0.0.0"
WEB_PORT = 5000

NEWS_SOURCES = {
    "en": [
        "techcrunch.com", "venturebeat.com", "forrester.com", 
        "gartner.com", "zdnet.com", "cncf.io", "devops.com"
    ],
    "zh": [
        "tech.163.com", "sina.com.cn", "qq.com", "ifeng.com",
        "caict.ac.cn", "c114.com.cn", "csdn.net", "infoq.com"
    ]
}
