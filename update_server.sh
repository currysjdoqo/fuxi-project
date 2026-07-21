#!/bin/bash

set -e

SERVER_IP="43.108.18.169"
PROJECT_DIR="/opt/fuxi"

echo "=== 习题库管理系统 - 更新脚本 ==="
echo ""

read -p "请确认已将最新代码上传到服务器并解压到 $PROJECT_DIR 目录 (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "请先上传并解压最新代码，然后重新运行此脚本"
    exit 1
fi

echo ""
echo "1. 进入项目目录..."
cd "$PROJECT_DIR"

echo ""
echo "2. 创建数据目录..."
mkdir -p data uploads
chown -R www-data:www-data data uploads 2>/dev/null || true
chmod -R 755 data uploads

echo ""
echo "3. 配置环境变量..."
cat > .env << EOF
ALLOWED_ORIGINS=http://localhost:80,http://localhost,http://127.0.0.1,http://$SERVER_IP
WRONG_QUESTION_REMOVE_THRESHOLD=5
DEEPSEEK_API_KEY=
EOF

echo ""
echo "4. 停止旧容器..."
docker-compose down 2>/dev/null || true

echo ""
echo "5. 重新构建并启动容器..."
docker-compose up -d --build

echo ""
echo "6. 等待服务启动..."
sleep 30

echo ""
echo "7. 检查容器状态..."
docker-compose ps

echo ""
echo "8. 查看后端日志..."
docker-compose logs backend --tail=50

echo ""
echo "9. 检查健康状态..."
curl -s http://localhost:8000/health || echo "健康检查失败"

echo ""
echo "=== 更新完成 ==="
echo "前端访问地址: http://$SERVER_IP"
echo "后端API地址: http://$SERVER_IP/api"