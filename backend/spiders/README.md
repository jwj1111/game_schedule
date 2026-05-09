# 爬虫模块 `backend/spiders/`

多游戏官网资讯爬取模块，基于 **Playwright**（无头浏览器渲染 JS 页面）+ **BeautifulSoup**（HTML 解析）。

---

## 文件清单

| 文件 | 职责 |
| --- | --- |
| `base.py` | `BaseSpider` 爬虫基类：浏览器管理、通用请求、各站点解析器（`parse_xxx`） |
| `sites.yaml` | 站点清单 + 运行参数 + 默认调度间隔配置 |
| `config.py` | 读取 `sites.yaml`，返回结构化的 `SpiderConfig`（dataclass） |
| `runner.py` | 批量执行入口：读配置 → 调 BaseSpider → 存 JSON（纯爬取，零 app 依赖） |

---

## 常用命令

所有命令在**项目根目录**下执行：

```powershell
# 只爬取，存 JSON
.\.venv\Scripts\python.exe -m backend.spiders.runner

# 只检查配置是否正确（不爬，秒出结果）
.\.venv\Scripts\python.exe -m backend.spiders.config
```

跑完后结果存在 `data/crawl_preview.json`（Git 忽略），可直接打开查看。

---

## 如何新增一个站点

**改两个文件，三步完成：**

### 第 1 步：`sites.yaml` 追加一项

```yaml
sites:
  # ... 已有站点 ...

  - game: 新游戏名        # 业务展示名（进数据库/前端）
    parser: 新游戏名      # 必须与 base.py 中注册的 key 一致
    url: https://xxx.com/news.html
    enabled: true
```

### 第 2 步：`base.py` 添加解析器

1. 在 `BaseSpider` 类中新增一个 `parse_xxx` 方法：

```python
def parse_xxx(self, html: str, target_url: str) -> List[Dict[str, Any]]:
    """新游戏解析逻辑"""
    items: List[Dict[str, Any]] = []
    # ... 根据站点逻辑解析 ...
    return items
```

2. 在 `__init__` 中的 `parser_registry` 注册：

```python
self.parser_registry = {
    # ... 已有解析器 ...
    "新游戏名": self.parse_xxx,
}
```

### 第 3 步：跑一次验证

```powershell
.\.venv\Scripts\python.exe -m backend.spiders.runner
```

确认新站点有条数输出、`crawl_preview.json` 中数据正确即可。

---

## 调试技巧

| 场景 | 做法 |
| --- | --- |
| 只爬某一个站点 | `sites.yaml` 中其他站点 `enabled: false` |
| 看浏览器实际加载 | `sites.yaml` 中 `headless: false` |
| 页面抓不到数据 | 先 `headless: false` 看页面渲染情况，再用 F12 确认 CSS 选择器 |

---

## 配置说明 `sites.yaml`

### `schedule` — 调度配置

```yaml
schedule:
  interval: 2h    # 默认爬取间隔，可由 .env 的 SPIDER_INTERVAL 覆盖
```

**`interval` 格式**：数字 + 单位，最小单位为分钟。

| 写法 | 含义 |
| --- | --- |
| `30m` | 每 30 分钟 |
| `2h` | 每 2 小时 |
| `1d` | 每天 |

> 手动运行 `backend.spiders.runner` 时，`interval` 仅用于配置检查/展示，不驱动定时任务；启动 FastAPI 后，APScheduler 会使用该间隔。若 `.env` 配置了 `SPIDER_INTERVAL`，则优先使用 `.env` 的值。

### `runtime` — 运行参数

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `headless` | bool | `true` | 无头模式；调试改 `false` 会弹出浏览器 |
| `ignore_https_errors` | bool | `false` | 忽略证书错误（内网/自签名用） |
| `timeout_seconds` | int | `15` | 单次请求超时（秒） |
| `retry_times` | int | `3` | 失败重试次数 |

### `sites[]` — 站点清单

| 字段 | 必填 | 说明 |
| --- | :---: | --- |
| `game` | 是 | 业务层游戏名 |
| `parser` | 是 | 解析器 key，必须与 `BaseSpider.parser_registry` 一致 |
| `url` | 是 | 爬取目标地址 |
| `enabled` | 否 | 默认 `true`；临时停爬置为 `false` |

---

## 数据字段

每条爬取结果包含：

```json
{
  "game": "游戏名",
  "info": "新闻标题",
  "link": "新闻详情页完整 URL"
}
```

---

## 容错机制

- **网络失败**：自动重试 `retry_times` 次（指数退避 1s/2s/4s），全失败返回空列表
- **解析异常**：`try-except` 兜底，打印错误信息后返回空列表
- **单站点失败不影响其他站点**，最终汇总中仅缺失该站点的数据

---

## 解析器注册示例

完整清单见 `base.py` 中 `parser_registry` 字典，以下仅举例说明命名规则：

| parser key | 方法名 | 站点 |
| --- | --- | --- |
| 火影忍者 | `parse_huoying` | hyrz.qq.com |
| DNF | `parse_dnf` | dnf.qq.com |
| 无畏契约 | `parse_valo` | val.qq.com |
