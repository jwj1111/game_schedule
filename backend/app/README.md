# 后端应用模块 `backend/app/`

FastAPI 服务 + 数据库 ORM + 预处理 + 定时调度。

---

## 文件清单

| 文件 | 职责 |
| --- | --- |
| `main.py` | FastAPI 入口：CORS 跨域、挂载路由、启动/关闭 APScheduler |
| `config.py` | 读 `.env`，双环境自动切换（本地 SQLite / 线上 MySQL） |
| `database.py` | SQLAlchemy engine / SessionLocal / Base / `get_db()` 依赖注入 |
| `models.py` | ORM 模型 `GameNews`（去重约束 UNIQUE(game, info)） |
| `schemas.py` | Pydantic 响应模型（接口返回的 JSON 结构） |
| `crud.py` | 数据库操作：`bulk_insert_new()` 去重入库 / `cleanup_expired()` 过期清理 |
| `pipeline.py` | 完整流水线：爬取 → 预处理 → 入库（编排 spiders + app） |
| `preprocessor.py` | 入库前预处理：筛选含"X月X日"的标题 + 提取 `online_date`（独立可替换） |
| `scheduler.py` | APScheduler 注册：定时爬取入库 + 定期过期清理 |
| `api/news.py` | 查询路由：全量 / 筛选 / 详情 / 游戏列表 |

---

## 启动与测试

```powershell
# 启动 FastAPI 服务（含定时任务）
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000

# 手动跑一次完整流水线（爬取 + 预处理 + 入库）
.\.venv\Scripts\python.exe -m backend.app.pipeline
```

- Swagger 接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/
- 停止：终端 `Ctrl+C`

启动时自动执行：建表（首次）→ 启动 APScheduler（定时爬取 + 定时清理）。

---

## 接口清单

| 接口 | 方法 | 参数 | 说明 |
| --- | --- | --- | --- |
| `/` | GET | - | 健康检查 |
| `/api/games` | GET | - | 数据库中所有游戏名（去重，前端下拉框用） |
| `/api/news` | GET | `game` `keyword` `start` `end` `page` `page_size` | 多条件筛选查询，按 online_date 降序，支持分页 |
| `/api/news/{news_id}` | GET | 路径参数 id | 单条详情 |

### `/api/news` 参数说明

| 参数 | 类型 | 必填 | 示例 |
| --- | --- | :---: | --- |
| `game` | string | 否 | `DNF` |
| `keyword` | string | 否 | `更新公告` |
| `start` | date | 否 | `2026-03-01` |
| `end` | date | 否 | `2026-04-30` |
| `page` | int | 否 | `1`（默认） |
| `page_size` | int | 否 | `50`（默认，最大 200） |

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

### `backend/spiders/sites.yaml`（爬取间隔）

```yaml
schedule:
  interval: 2h    # 支持 m/h/d，如 30m / 2h / 1d
```

---

## 定时任务

| 任务 | 触发规则 | 配置位置 |
| --- | --- | --- |
| 定时爬取 + 预处理 + 入库 | 固定间隔（`sites.yaml` 的 `interval`） | `backend/spiders/sites.yaml` |
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
2. `runner.py` 和 `scheduler.py` 改一行 import
3. 其余代码零改动

函数签名契约：

```python
def preprocess(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 输入: [{"game", "info", "link"}, ...]
    # 输出: [{"game", "info", "link", "online_date": date}, ...]
```

---

## 数据库表结构

```
game_news
├── id            INTEGER PRIMARY KEY AUTOINCREMENT
├── game          VARCHAR(50)   NOT NULL, INDEX
├── info          VARCHAR(500)  NOT NULL
├── link          VARCHAR(1000) NOT NULL
├── online_date   DATE          NOT NULL, INDEX
├── created_at    DATETIME      NOT NULL DEFAULT now
└── UNIQUE(game, info)          -- 去重约束
```

- **去重**：`game + info` 联合唯一，同游戏同标题不重复入库
- **清理**：`online_date < 今天 - N 天` 的记录直接删除
- **双环境**：同一份 ORM 代码，SQLite / MySQL 自动切换
