# 游戏时间轴看板

多游戏资讯聚合 + 时间轴可视化看板。
技术栈：**Python 3.9+ / FastAPI / SQLAlchemy 2.0+ / APScheduler / Vue3 CDN / Tailwind CSS CDN**

> 开发前请务必通读 [`ai开发规范.md`](./ai开发规范.md)。

---

## 目录结构

```
game_schedule/
├── backend/          # FastAPI + 爬虫 + 定时 + 推送
│   ├── app/          # 应用主包
│   │   └── api/      # 路由分组
│   ├── spiders/      # 爬虫模块
│   └── requirements.txt
├── frontend/
│   └── index.html    # 单 HTML，Vue3 + Tailwind（CDN）
├── deploy/           # Docker 部署配置（第二阶段再建）
├── data/             # 本地 SQLite（Git 忽略）
├── logs/             # 运行日志（Git 忽略）
├── .venv/            # Python 虚拟环境（Git 忽略）
├── .env.example      # 配置模板
├── .gitignore
├── README.md
└── ai开发规范.md
```

---

## 本地快速开始

### 1. 创建虚拟环境（仅首次）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### 2. 启动后端（待实现 `backend/app/main.py` 后）

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

接口文档：<http://localhost:8000/docs>

### 3. 打开前端

直接双击 `frontend/index.html`，或用 VSCode Live Server 打开。

---

## 迭代部署

本地修改 → `git commit` → `git push` → 服务器 `git pull` → `docker-compose up -d --build`。
详见 `ai开发规范.md` 第五章。

---

## 注意

- ❌ 不要在本地安装 Docker / MySQL / Node.js
- ❌ 不要把 `.env`、`*.db`、`.venv/` 提交到 Git
- ❌ 不要把前端改造成工程化项目
