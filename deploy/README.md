# 部署指南

## 前置要求

- Linux 服务器（推荐 Ubuntu 22.04+）
- Docker 24+
- Docker Compose v2+
- Git

## 首次部署

### 1. 克隆仓库

```bash
git clone <your-repo-url> /opt/game_schedule
cd /opt/game_schedule
```

### 2. 配置环境变量

```bash
cp .env.example .env
vim .env
```

**必须修改的配置项：**

| 变量 | 说明 |
|------|------|
| `ENV` | 改为 `prod` |
| `MYSQL_PASSWORD` | 设置应用数据库密码 |
| `MYSQL_ROOT_PASSWORD` | 设置 MySQL root 密码 |
| `ADMIN_PASSWORD` | 设置管理员登录密码 |
| `AUTH_SECRET_KEY` | 设置一个随机密钥（可用 `openssl rand -base64 32` 生成） |

### 3. 启动服务

```bash
cd deploy
docker compose up -d --build
```

### 4. 验证

```bash
# 检查容器状态
docker compose ps

# 查看应用日志
docker compose logs -f app

# 测试 API
curl http://localhost/api/
```

## 日常迭代

```bash
cd /opt/game_schedule
git pull
cd deploy
docker compose up -d --build
```

## 常用命令

```bash
# 查看日志
docker compose logs -f app
docker compose logs -f nginx

# 重启单个服务
docker compose restart app

# 停止服务（保留数据）
docker compose down

# ⚠️ 危险：停止并删除数据卷
# docker compose down -v
```

## 架构图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│   FastAPI   │────▶│    MySQL    │
│   :80       │     │   :8000     │     │   :3306     │
│             │     │             │     │             │
│ 前端静态资源 │     │ API + 爬虫   │     │  数据持久化  │
└─────────────┘     └─────────────┘     └─────────────┘
```

## 注意事项

1. **绝对禁止** `docker compose down -v`，会删除 MySQL 数据
2. **绝对禁止** 在服务器上直接修改代码，所有改动走 git
3. 首次启动 MySQL 初始化需要约 30 秒，app 会等待 healthcheck 通过后才启动
4. Playwright 镜像较大（~2GB），首次构建需要较长时间
5. 如需 HTTPS，建议在 Nginx 前再加一层 Caddy 或 Certbot
