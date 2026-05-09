# 游戏时间轴看板项目 全流程开发迭代规范

> **AI Vibe Coding 专用规范文档**
> 本文档为项目开发的最高准则，AI 在执行任何开发任务时必须严格遵循。

---

## 目录

- [一、项目核心技术栈](#一项目核心技术栈ai严格遵守禁止私自更改)
- [二、项目核心原则](#二项目核心原则ai绝对不可违反)
- [三、项目骨架参考](#三项目骨架参考目录命名与环境位置)
- [四、分阶段完整开发流程](#四分阶段完整开发流程按顺序执行禁止跳步)
- [五、日常迭代更新规范](#五日常迭代更新规范永久固定流程)
- [六、绝对禁止事项](#六绝对禁止事项ai严禁执行)
- [七、AI Vibe Coding 指令前缀](#七ai-vibe-coding-指令前缀直接复制使用)

---

## 一、项目核心技术栈（AI严格遵守，禁止私自更改）

### 后端 / 爬虫

| 项目 | 选型 |
| --- | --- |
| 开发语言 | Python 3.10+（推荐 Python 3.11） |
| 数据库 | 本地 SQLite、线上 MySQL |
| ORM 框架 | SQLAlchemy 2.0+ |
| 后端接口 | FastAPI |
| 定时任务 | APScheduler |
| 部署工具 | Docker + Docker Compose |

### 前端

- **构建工具**：Vite
- **核心框架**：Vue3（单文件组件，组合式 API setup）
- **样式框架**：Tailwind CSS
- **UI 组件库**：Element Plus（按需自动引入）
- **部署**：Vite 构建为静态资源，Docker 中 Nginx 托管

---

## 二、项目核心原则（AI绝对不可违反）

1. **极简开发**：本地全程无 Docker、无 MySQL，开箱即写
2. **环境隔离**：本地与线上配置完全分离，代码与数据物理隔离
3. **数据安全**：任何迭代不删除、不污染线上数据库存量数据
4. **流程不变**：前端迭代不破坏原有 Git、Docker 部署、服务器更新流程
5. **禁止过度设计**：不引入多余中间件、不拆分复杂模块、代码简洁易懂
6. **一键迭代**：所有功能更新仅需本地修改 → Git 提交 → 服务器拉取 → 重启

---

## 三、项目骨架参考（目录、命名与环境位置）

> 本章为**参考性架构**，给出目录层级与"一定会有的关键文件"，不限定每个模块的具体实现。
> AI 在新建或补全项目时，按此骨架组织；对未列出的细节可自由发挥，但**不得违反前两章的原则与本章的位置约定**。

### 1. 顶层目录树

```
game_schedule/                  # 项目根（= Git 仓库根）
│
├── backend/                    # 后端：FastAPI + 爬虫 + 定时任务 + 推送
│   ├── app/                    # FastAPI 应用主包（接口、ORM、配置、调度、通知）
│   │   └── api/                # 路由分组（查询类、管理类等）
│   ├── spiders/                # 爬虫模块（每站点一个解析函数或一个类）
│   └── requirements.txt        # 后端依赖清单（唯一依赖来源）
│
├── frontend/                   # 前端：Vite + Vue3 工程
│   ├── src/                    # 源码目录
│   ├── package.json            # 前端依赖
│   └── vite.config.js          # Vite 配置
│
├── deploy/                     # 部署配置（第二阶段才创建，第一阶段留空或不建）
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
│
├── data/                       # 本地 SQLite 文件存放处（Git 忽略）
├── logs/                       # 运行日志（Git 忽略）
├── .venv/                      # Python 虚拟环境（Git 忽略，仅本地存在）
│
├── .env.example                # 配置模板（提交 Git，密码用占位符）
├── .env                        # 真实配置（Git 忽略，本地/服务器各自维护）
├── .gitignore
├── README.md
└── ai开发规范.md
```

### 2. 关键文件清单（一定会有的）

| 路径 | 作用 | 是否提交 Git |
| --- | --- | :---: |
| `backend/requirements.txt` | 后端依赖清单 | ✅ |
| `backend/app/main.py` | FastAPI 入口，挂路由、启调度 | ✅ |
| `backend/app/config.py` | 读 `.env`，做本地/线上数据库切换 | ✅ |
| `backend/app/database.py` | SQLAlchemy engine / Session / Base | ✅ |
| `backend/app/models.py` | ORM 数据表模型 | ✅ |
| `backend/app/schemas.py` | Pydantic 响应模型 | ✅ |
| `backend/app/crud.py` | 数据库读写（去重入库 / 过期清理） | ✅ |
| `backend/app/pipeline.py` | 完整流水线：爬取 → 预处理 → 入库 | ✅ |
| `backend/app/preprocessor.py` | 入库前预处理（筛选 + 日期提取，独立可替换） | ✅ |
| `backend/app/scheduler.py` | APScheduler 定时任务注册 | ✅ |
| `backend/app/auth.py` | 轻量管理员认证（密码验证、HMAC 签名 Token 签发） | ✅ |
| `backend/app/notifier.py` | 企业微信机器人推送封装（后续开发，当前未实现） | 规划中 |
| `backend/spiders/` | 爬虫代码（基类 + 批量爬取入口） | ✅ |
| `frontend/` | Vite + Vue3 前端工程 | ✅ |
| `.env.example` | 配置模板 | ✅ |
| `.gitignore` | Git 忽略规则 | ✅ |
| `README.md` | 项目说明 | ✅ |
| `.env` | 真实配置 | ❌ |
| `.venv/` | 虚拟环境 | ❌ |
| `data/*.db` | 本地 SQLite 数据 | ❌ |
| `logs/*` | 运行日志 | ❌ |

### 3. 环境与产物位置约定

| 项 | 位置 | 说明 |
| --- | --- | --- |
| Python 虚拟环境 | `<项目根>/.venv/` | IDE 自动识别；**禁止**放全局目录或子模块内 |
| 本地配置 | 本地默认**不创建** `.env`，`config.py` 须有合理默认值可直接跑 | 规范要求"本地仅保留模板" |
| 线上配置 | 服务器 `cp .env.example .env` 后填真实值 | 仅服务器持有 |
| 本地数据库 | `data/game_schedule.db`（SQLite，自动生成） | `.gitignore` 屏蔽 |
| 线上数据库 | MySQL（由 docker-compose 管理，数据卷持久化） | 不进 Git |
| 运行日志 | `logs/` | `.gitignore` 屏蔽 |
| 临时调试产物 | 就地生成（如 `data/crawl_preview.json`、临时导出文件），用后自行清理 | `.gitignore` 屏蔽 |

### 4. 命名与归位原则

- **后端业务代码**一律放在 `backend/app/`，爬虫单独放 `backend/spiders/`，app 可调用 spiders，spiders 不依赖 app。禁止前端目录出现 Python 文件。
- **前端代码**统一放在 `frontend/` 下，使用 Vite 构建；构建产物（`dist/`）不提交 Git，由 Docker 构建时生成。
- **部署文件**全部收敛到 `deploy/`，与业务代码隔离；第一阶段本地开发**不创建** `deploy/`，避免误用。
- **模型、接口、调度、推送**四类代码各占一个文件（`models.py` / `api/*.py` / `scheduler.py` / `notifier.py`），不做过度拆分。

### 5. `.gitignore` 最小必含项

```gitignore
# 虚拟环境
.venv/
venv/

# Python 产物
__pycache__/
*.pyc

# 配置与数据
.env
*.db
data/
logs/

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# 临时导出文件
*.xlsx

# 前端构建产物
frontend/dist/
frontend/node_modules/
```

### 6. 何时创建 `deploy/`

- **第一阶段（本地开发）**：不创建，专注本地 SQLite + FastAPI + Vite 开发服务器。
- **第二阶段（首次上线前）**：一次性创建 `Dockerfile`、`docker-compose.yml`、`nginx.conf`，此后按迭代规范维护，**禁止随业务代码频繁改动**。

---

## 四、分阶段完整开发流程（按顺序执行，禁止跳步）

### 第一阶段：本地基础开发（无服务器、无 Docker、纯本地）

#### 1. 项目初始化

- 创建 Python 虚拟环境，生成 `requirements.txt` 管理所有依赖
- 编写 `.gitignore` 文件，屏蔽本地数据库、虚拟环境、私密配置
- 新建 `.env.example` 配置模板，存放公共配置，密码用占位符
- 编写数据库双环境切换代码，本地自动连接 SQLite，线上自动连接 MySQL

#### 2. 爬虫模块开发

- 编写爬虫逻辑，完成目标数据爬取、清洗、格式化
- 配置 SQLAlchemy 数据表模型，定义字段规范
- 实现数据入库逻辑，爬取数据无缝写入本地 SQLite
- 集成 APScheduler，实现定时爬取功能，本地测试正常运行

#### 3. FastAPI 后端开发

- 搭建基础 FastAPI 服务，配置跨域支持
- 编写数据查询接口：
  - 统一日历查询（支持游戏、负责人、时间、关键词筛选）
  - 资讯速览查询（当天、未来15天、过去7天）
  - 游戏名与负责人列表查询
- 编写管理员认证接口：
  - 密码验证登录与 HMAC 签名 Bearer Token 签发
- 编写数据管理接口：
  - 爬虫数据标注（优先级、别名、资源位、隐藏）
  - 自定义事件 CRUD
  - 游戏负责人映射 CRUD
  - 定时过期数据清理
- 预留企业微信机器人推送接口规划（后续开发）
- 本地接口测试：通过 `localhost:8000/docs` 验证所有接口正常

#### 4. Vue3 前端开发

- 使用 Vite 初始化 Vue3 项目，集成 Tailwind CSS
- 采用组合式 API（setup）编写，按需引入 UI 组件库
- 实现核心功能：
  - 日历主面板：按月网格展示，支持年月跳转
  - 资讯速览面板：当天及近期重要事项的按日分组概览
  - 多条件筛选：按游戏多选、负责人、时间范围、关键词搜索
  - 单元格标签化展示，优先级色系映射
  - 点击日期弹出详细侧栏，支持就地编辑优先级、资源位、隐藏等属性
  - 管理员认证与权限控制：登录弹窗、受保护操作鉴权
  - 辅助面板：自定义事件管理、月度统计、负责人设置
- 调用 FastAPI 接口，实现前后端数据联调
- 本地通过 `npm run dev` 启动 Vite 开发服务器测试

#### 5. 功能联调

- 本地完成 爬虫 → 数据库 → 后端接口 → 前端页面 全链路测试
- 验证定时任务、数据筛选等已实现功能正常运行
- 所有业务逻辑无 BUG 后，再进入下一阶段

---

### 第二阶段：部署前置配置（仅执行一次）

#### 1. Git 配置规范

- `.gitignore` 必须包含：本地 `.db` 文件、`venv`、`__pycache__`、`.env`、日志文件
- 仅将业务代码、配置模板、Docker 配置提交至 Git
- **禁止提交**：私密配置、本地数据库、临时缓存文件

#### 2. Docker 配置编写

- 编写 Python 服务 Dockerfile，基于 Python 镜像，安装项目依赖
- 编写 `docker-compose.yml`，包含 MySQL、FastAPI + 爬虫、Nginx 前端服务
- MySQL 配置数据卷持久化，确保容器删除数据不丢失
- Nginx 托管前端构建产物（Vite build 输出的静态文件）

#### 3. 环境配置分离

- 本地不创建真实 `.env` 文件，仅保留 `.env.example` 模板
- 线上私密配置（数据库密码、企微密钥）仅在服务器编写

---

### 第三阶段：服务器上线部署（仅执行一次）

1. 服务器安装 Docker + Docker Compose，开放对应端口
2. 服务器克隆 Git 代码仓库，进入项目目录
3. 执行 `cp .env.example .env`，通过 `nano` 编辑 `.env`，填写真实配置
4. 执行 `docker-compose up -d`，一键启动所有服务
5. 验证前端页面、后端接口、爬虫、定时任务、推送功能全部正常

---

## 五、日常迭代更新规范（永久固定流程）

### 通用迭代步骤（所有修改均遵循）

1. **本地修改**：在本地完成代码修改 / 功能新增，全程用本地 SQLite 测试
   - 后端：修改爬虫、接口、定时任务、推送逻辑
   - 前端：修改 Vue 组件、Tailwind 样式，`npm run dev` 本地热更新
2. **本地自测**：确保修改后功能正常，无 BUG、无报错
3. **Git 提交**：
   ```bash
   git add .
   git commit -m "功能说明"
   git push
   ```
4. **服务器更新**：
   - 服务器进入项目目录，执行 `git pull` 拉取最新代码
   - 执行 `docker-compose up -d --build` 重启相关服务
   - 前端修改需 `docker-compose up -d --build` 重新构建

### 分场景迭代要求

#### 1. 新增 / 修改后端功能

- 正常修改 Python 代码，更新 `requirements.txt`（如需）
- 本地测试通过后，按通用流程迭代
- **禁止编写删库、清空数据表的危险代码**

#### 2. 新增 / 修改前端功能

- 修改 `frontend/src/` 下的 Vue 组件和样式
- 本地 `npm run dev` 热更新测试
- 线上部署时 Docker 自动执行 `npm run build`，无需手动构建

#### 3. 修改配置参数

- 公共配置修改本地 `.env.example`，提交 Git
- 私密配置直接在服务器修改 `.env`，执行 `docker-compose restart`

#### 4. 数据库表结构变更

- 修改 SQLAlchemy 模型，本地测试正常
- 线上通过 `ALTER TABLE` 语句手动更新，**禁止使用 `db.drop_all()`**

---

## 六、绝对禁止事项（AI严禁执行）

| 序号 | 禁止事项 |
| :---: | --- |
| 1 | ❌ 禁止本地安装 Docker、MySQL |
| 2 | ❌ 禁止在代码中硬编码密码、密钥、接口地址 |
| 3 | ❌ 禁止提交 `.env`、本地数据库文件、`node_modules`、`dist` 至 Git 仓库 |
| 4 | ❌ 禁止直接在服务器修改代码，所有修改必须本地完成 |
| 5 | ❌ 禁止执行 `docker-compose down -v`，避免删除数据库数据卷 |
| 6 | ❌ 禁止删除服务器项目文件，仅用 `git pull` 增量更新 |
| 7 | ❌ 禁止编写无 WHERE 条件的 DELETE、TRUNCATE 语句 |

---

## 七、AI Vibe Coding 指令前缀（直接复制使用）

> 请严格遵循本《游戏时间轴看板项目 全流程开发迭代规范》，基于 **Python + FastAPI + SQLAlchemy + Vite + Vue3 + Tailwind CSS** 技术栈，帮我实现【填写具体功能需求】。
>
> **要求**：
> 1. 前端使用 Vite + Vue3 组合式 API + Tailwind CSS
> 2. 后端遵循双环境数据库切换，代码规范无冗余
> 3. 不破坏原有迭代部署流程，代码可直接上线
> 4. 功能完整，本地可直接运行测试

---

*本规范为项目开发最高准则，任何代码产出必须通过本规范校验。*
