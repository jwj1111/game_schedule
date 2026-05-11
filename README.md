# 游戏时间轴看板

多游戏资讯聚合 + 时间轴可视化看板。
技术栈：**Python 3.10+ / FastAPI / SQLAlchemy 2.0+ / APScheduler / Vite / Vue3 / Tailwind CSS v4**

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
├── frontend/         # Vite + Vue3 前端工程
│   ├── src/          # 源码目录
│   ├── package.json  # 前端依赖
│   └── vite.config.js# Vite 配置
├── deploy/           # Docker 部署配置
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

### 1. 启动后端

```powershell
# 1. 创建虚拟环境并安装依赖（仅首次）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

# 2. 首次使用爬虫需安装 Playwright 浏览器内核
.\.venv\Scripts\python.exe -m playwright install chromium

# 3. 启动 FastAPI 服务（在项目根目录执行）
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000
```

接口文档：<http://localhost:8000/docs>

### 2. 启动前端

```powershell
# 1. 按 lock 文件安装依赖（仅首次或依赖变化后）
cd frontend
npm ci

# 2. 启动开发服务器
npm run dev
```

打开浏览器访问输出的 `localhost` 地址，Vite 代理会自动将 `/api` 转发到 `localhost:8000`。

---

## 迭代部署

本地修改 → `git commit` → `git push` → 服务器 `git pull` → `docker compose up -d --build`。
详见 `ai开发规范.md` 第五章。

---

## 注意

- ❌ 不要在本地安装 Docker / MySQL
- ❌ 不要把 `.env`、`*.db`、`.venv/`、`node_modules/`、`frontend/dist/` 提交到 Git
