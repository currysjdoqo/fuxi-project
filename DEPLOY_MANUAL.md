# 习题库管理系统 - 手动部署指南

## 服务器信息
- 公网IP: 43.108.18.169
- 系统: Linux (预装 Docker 26.1.3)

## 部署步骤

### 第一步：登录服务器
通过云服务商控制台登录到服务器。

### 第二步：安装必要工具
```bash
# 更新系统
apt update && apt upgrade -y

# 安装 git 和 docker-compose
apt install -y git docker-compose
```

### 第三步：创建项目目录
```bash
mkdir -p /opt/fuxi
cd /opt/fuxi
```

### 第四步：上传项目文件
有两种方式上传项目：

**方式A：通过 Git 克隆（推荐）**
```bash
# 如果项目已推送到 GitHub/GitLab
git clone <你的仓库地址> .
```

**方式B：通过控制台文件上传**
将本地项目打包后上传到服务器：
```bash
# 在本地执行（Windows PowerShell）
Compress-Archive -Path * -DestinationPath fuxi.zip

# 在服务器执行
unzip fuxi.zip
```

### 第五步：配置环境变量
```bash
# 创建 .env 文件
cat > .env << EOF
ALLOWED_ORIGINS=http://localhost:80,http://localhost,http://127.0.0.1,http://43.108.18.169
WRONG_QUESTION_REMOVE_THRESHOLD=5
DEEPSEEK_API_KEY=
EOF
```

### 第六步：创建数据目录
```bash
mkdir -p /opt/fuxi/data /opt/fuxi/uploads
chown -R www-data:www-data /opt/fuxi/data /opt/fuxi/uploads
```

### 第七步：启动服务
```bash
cd /opt/fuxi
docker-compose up -d --build
```

### 第八步：检查状态
```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 健康检查
curl http://localhost:8000/health
```

## 访问地址
- 前端: http://43.108.18.169
- 后端API: http://43.108.18.169/api
- 健康检查: http://43.108.18.169/api/health

## 常见问题

### 1. Docker 端口被占用
```bash
# 检查端口占用
netstat -tlnp | grep 80

# 停止占用服务
systemctl stop nginx  # 如果有nginx占用80端口
```

### 2. 容器启动失败
```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend
```

### 3. 数据库问题
数据库使用 SQLite，数据文件存储在 `/opt/fuxi/data` 目录。

### 4. AI 功能不可用
需要在 `.env` 文件中配置 `DEEPSEEK_API_KEY`，或在系统设置中通过前端界面配置。

## 安全建议
1. 配置防火墙，只开放必要端口（80, 443）
2. 考虑配置 HTTPS（使用 Let's Encrypt）
3. 定期更新系统和容器镜像
4. 不要在公开仓库中提交 `.env` 文件
