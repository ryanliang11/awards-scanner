# IT运维奖项扫描智能体 (Awards Scanner)

## 快速部署到 Streamlit Cloud

### 步骤1: 创建GitHub仓库

1. 打开 https://github.com/new
2. Repository name 填写: `awards-scanner`
3. 选择 **Public**
4. 点击 **Create repository**

### 步骤2: 上传代码

在仓库页面点击 **uploading an existing file**，上传以下文件：
- `app.py`
- `config.py`
- `requirements.txt`
- 整个 `scanner` 文件夹
- 整个 `storage` 文件夹
- 整个 `data` 文件夹（如果有的话）

或者在本地执行：
```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/你的用户名/awards-scanner.git
git push -u origin main
```

### 步骤3: 部署到Streamlit

1. 打开 https://share.streamlit.io
2. 用GitHub账号登录
3. 点击 **New app**
4. 选择刚才创建的仓库
5. Main file path 填写: `app.py`
6. 点击 **Deploy!**

### 部署完成！

部署成功后，Streamlit会给你一个网址，比如：
`https://awards-scanner.streamlit.app`

打开这个网址就能使用了！🎉

---

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 功能说明

- 🏆 扫描IT运维相关奖项新闻
- 🌐 支持中英文
- 📊 数据统计
- 🔍 关键词搜索
- 📂 分类筛选
- 🔄 手动触发扫描

扫描关键词: AIOps, 智能运维, Gartner, Forrester, 信通院, DevOps, SRE 等
