#!/bin/bash

set -e

echo "=== 习题库管理系统服务器端部署脚本 ==="
echo ""

SERVER_IP="43.108.18.169"
PROJECT_DIR="/opt/fuxi"

echo "1. 更新系统..."
apt update && apt upgrade -y

echo ""
echo "2. 安装必要工具..."
apt install -y docker-compose git unzip curl

echo ""
echo "3. 创建项目目录..."
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo ""
echo "4. 下载部署包..."
echo "请将 fuxi-deploy.zip 上传到服务器，然后按回车继续..."
read

if [ -f "fuxi-deploy.zip" ]; then
    echo "5. 解压部署包..."
    unzip -o fuxi-deploy.zip
else
    echo "错误: fuxi-deploy.zip 未找到，请先上传文件"
    exit 1
fi

echo ""
echo "6. 创建数据目录..."
mkdir -p data uploads
chown -R www-data:www-data data uploads 2>/dev/null || true

echo ""
echo "7. 配置环境变量..."
cat > .env << EOF
ALLOWED_ORIGINS=http://localhost:80,http://localhost,http://127.0.0.1,http://$SERVER_IP
WRONG_QUESTION_REMOVE_THRESHOLD=5
DEEPSEEK_API_KEY=
EOF

echo ""
echo "8. 启动 Docker Compose..."
docker-compose up -d --build

echo ""
echo "9. 等待服务启动..."
sleep 15

echo ""
echo "10. 检查容器状态..."
docker-compose ps

echo ""
echo "11. 检查健康状态..."
curl -s http://localhost:8000/health || echo "健康检查失败"

echo ""
echo "=== 部署完成 ==="
echo "前端访问地址: http://$SERVER_IP"
echo "后端API地址: http://$SERVER_IP/api"
echo "健康检查: http://$SERVER_IP/api/health"
