# 后端应用模块 `backend/app/`

FastAPI 服务 + 数据库 ORM + 预处理 + 定时调度。

---

## 文件清单

| 文件 | 职责 |
| --- | --- |
| `main.py` | FastAPI 入口：CORS 跨域、挂载路由、启动/关闭 APScheduler |
| `config.py` | 读 `.env`，双环境自动切换（本地 SQLite / 线上 MySQL） |
| `database.py` | SQLAlchemy engine / SessionLocal / Base / `get_db()` 依赖注入 |
| `models.py` | ORM 模型：GameNews / UserAnnotation / UserEvent / GameOwner |
| `schemas.py` | Pydantic 请求体 + 响应模型 |
| `crud.py` | 数据库操作：爬虫入库 / 过期清理 / 标注 / 事件 / 负责人 CRUD |
| `pipeline.py` | 完整流水线：爬取 → 预处理 → 入库 |
| `preprocessor.py` | 入库前预处理：筛选含"X月X日"的标题 + 提取 `online_date`（独立可替换） |
| `scheduler.py` | APScheduler 注册：定时爬取入库 + 定期过期清理 |
| `auth.py` | 轻量管理员认证：密码验证与 HMAC 签名 Token 签发解析 |
| `api/auth.py` | 管理员认证接口（登录、状态、退出） |
| `api/news.py` | 统一日历查询、资讯速览查询 + 游戏列表 |
| `api/annotations.py` | 标注 CRUD（针对爬虫数据的附加属性） |
| `api/events.py` | 自定义事件 CRUD |
| `api/owners.py` | 游戏负责人管理 |
| `api/dbadmin.py` | 数据库管理彩蛋接口（需管理员权限） |

---

## 启动与测试

```powershell
# 启动 FastAPI 服务（含定时任务）
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000

# 手动跑一次完整流水线（爬取 + 预处理 + 入库）
.\.venv\Scripts\python.exe -m backend.app.pipeline
```

- Swagger 接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/
- 停止：终端 `Ctrl+C`

启动时自动执行：建表（首次）→ 启动 APScheduler（定时爬取 + 定时清理）。

---

## 接口清单

### 查询

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/` | GET | 健康检查 |
| `/api/calendar` | GET | 统一日历查询（合并爬虫+标注+事件），按月加载 |
| `/api/overview` | GET | 资讯速览查询（过去24小时入库+未来15天+过去7天相关事项） |
| `/api/games` | GET | 所有游戏名（爬虫+事件+负责人三表去重） |
| `/api/owner-names` | GET | 所有负责人姓名（去重，供筛选下拉框使用） |
| `/api/hidden` | GET | 所有已隐藏的爬虫数据（用于恢复显示，需管理员权限） |

#### `/api/calendar` 参数

| 参数 | 类型 | 必填 | 示例 |
| --- | --- | :---: | --- |
| `start_date` | date | 是 | `2026-04-01` |
| `end_date` | date | 是 | `2026-04-30` |
| `games` | string | 否 | `DNF,LOL`（逗号分隔） |
| `owners` | string | 否 | `张三,李四`（逗号分隔） |
| `keyword` | string | 否 | `更新公告` |

### 认证

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/auth/login` | POST | 管理员密码登录 |
| `/api/auth/status` | GET | 查询当前管理员登录状态 |
| `/api/auth/logout` | POST | 退出管理员登录 |

### 标注

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/annotations/{news_id}` | GET | 获取某条爬虫数据的标注 |
| `/api/annotations/{news_id}` | PUT | 创建或更新标注（优先级/别名/资源位/隐藏） |

### 自定义事件

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/events` | POST | 新建事件 |
| `/api/events/{id}` | PUT | 修改事件 |
| `/api/events/{id}` | DELETE | 删除事件（物理删除） |

### 游戏负责人

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/owners` | GET | 全部游戏负责人 |
| `/api/owners/{game}` | GET | 单个游戏负责人 |
| `/api/owners` | POST | 新增游戏负责人 |
| `/api/owners/{game}` | PUT | 修改负责人列表 |

### 数据库管理彩蛋

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/dbadmin/tables` | GET | 表列表 |
| `/api/dbadmin/tables/{table}/schema` | GET | 表结构 |
| `/api/dbadmin/tables/{table}/rows` | GET/POST | 查询 / 新增行 |
| `/api/dbadmin/tables/{table}/rows/{id}` | PUT/DELETE | 修改 / 删除行 |
| `/api/dbadmin/tables/{table}/rows/batch-delete` | POST | 批量删除（body: `{"ids": [...]}`, 上限500条） |
| `/api/dbadmin/status` | GET | 系统运行状态（调度器+数据库+服务器） |

---

## 配置参数速查

### `.env.example`（数据库 + 清理）

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `ENV` | `local` | `local` = SQLite，`prod` = MySQL |
| `SQLITE_PATH` | `./data/game_schedule.db` | 本地数据库路径 |
| `MYSQL_*` | 占位符 | 线上 MySQL 连接信息 |
| `DATA_RETENTION_DAYS` | `60` | 过期天数（0 = 永不删除） |
| `CLEANUP_DAY` | `mon` | 清理在星期几执行（mon~sun） |
| `CLEANUP_HOUR` | `3` | 清理在几点执行（0~23） |
| `SPIDER_INTERVAL` | `8h` | 爬虫调度间隔覆盖值，支持 `30m` / `2h` / `1d`；非空时优先于 `sites.yaml` |
| `ADMIN_PASSWORD` | 无 | 管理员登录密码（为空则禁止登录） |
| `AUTH_SECRET_KEY` | 留空则自动生成 | HMAC Token 签名密钥；生产环境建议显式配置强随机值 |
| `AUTH_TOKEN_EXPIRE_SECONDS` | `604800` | 登录 Token 过期时间（秒），默认 7 天 |

### `backend/spiders/sites.yaml`（爬取间隔）

```yaml
schedule:
  interval: 2h    # 支持 m/h/d，如 30m / 2h / 1d
```

---

## 定时任务

| 任务 | 触发规则 | 配置位置 |
| --- | --- | --- |
| 定时爬取 + 预处理 + 入库 | 固定间隔 | 默认 `backend/spiders/sites.yaml`，可由 `.env` 的 `SPIDER_INTERVAL` 覆盖 |
| 定期过期清理 | 每周某天某时（cron） | `.env.example` 的 `CLEANUP_DAY` + `CLEANUP_HOUR` |

---

## 预处理模块 `preprocessor.py`

**独立可替换模块**，未来可换成 AI 版本，只需保持函数签名不变。

### 当前规则

1. 正则匹配标题中的"X月X日"，不含日期的标题丢弃
2. 多个日期取第一个
3. 跨年处理：±5 个月窗口推断年份

### 跨年逻辑

```
diff = 标题月份 - 当前月份
diff > 5   → 去年
diff < -5  → 明年
else       → 今年
```

### 如何替换为 AI 版本

1. 新建 `preprocessor_ai.py`，实现同签名的 `preprocess()` 函数
2. `pipeline.py` 改一行 import
3. 其余代码零改动

函数签名契约：

```python
def preprocess(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 输入: [{"game", "info", "link"}, ...]
    # 输出: [{"game", "info", "link", "online_date": date}, ...]
```

---

## 数据库表结构

### `game_news`（爬虫原始数据，只读）

```
├── id            INTEGER PRIMARY KEY AUTOINCREMENT
├── game          VARCHAR(50)   NOT NULL, INDEX
├── info          VARCHAR(500)  NOT NULL
├── link          VARCHAR(1000) NOT NULL
├── online_date   DATE          NOT NULL, INDEX
├── created_at    DATETIME      NOT NULL DEFAULT now
└── UNIQUE(game, info)
```

### `user_annotation`（用户标注，关联爬虫表）

```
├── id              INTEGER PRIMARY KEY AUTOINCREMENT
├── news_id         INTEGER NOT NULL, UNIQUE, FK → game_news.id (CASCADE)
├── priority        INTEGER NOT NULL DEFAULT 0    (3=高/2=中/1=低/0=无)
├── alias           VARCHAR(200) NOT NULL DEFAULT ''
├── resource_ready  BOOLEAN NOT NULL DEFAULT FALSE
└── hidden          BOOLEAN NOT NULL DEFAULT FALSE
```

### `user_event`（自定义事件）

```
├── id              INTEGER PRIMARY KEY AUTOINCREMENT
├── game            VARCHAR(50)  NOT NULL, INDEX
├── description     VARCHAR(500) NOT NULL
├── event_date      DATE         NOT NULL, INDEX
├── priority        INTEGER NOT NULL DEFAULT 0
├── resource_ready  BOOLEAN NOT NULL DEFAULT FALSE
├── alias           VARCHAR(200) NOT NULL DEFAULT ''
└── created_at      DATETIME NOT NULL DEFAULT now
```

### `game_owner`（游戏负责人映射）

```
├── id      INTEGER PRIMARY KEY AUTOINCREMENT
├── game    VARCHAR(50) NOT NULL, UNIQUE, INDEX
└── owners  JSON NOT NULL DEFAULT []
```

- **去重**：`game_news` 按 `game + info` 联合唯一
- **过期过滤**：`online_date` 超过 `DATA_RETENTION_DAYS` 的数据不入库（防止清理后又被爬回）
- **级联**：删除 `game_news` 记录时，关联的 `user_annotation` 自动删除
- **双环境**：同一份 ORM 代码，SQLite / MySQL 自动切换
