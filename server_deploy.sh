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
chmod -R 755 data uploads

echo ""
echo "7. 配置环境变量..."
cat > .env << EOF
ALLOWED_ORIGINS=http://localhost:80,http://localhost,http://127.0.0.1,http://$SERVER_IP
WRONG_QUESTION_REMOVE_THRESHOLD=5
DEEPSEEK_API_KEY=
EOF

echo ""
echo "8. 确保 Docker 环境可用..."
docker --version || (echo "Docker 未安装，请先安装 Docker"; exit 1)
docker-compose --version || (echo "docker-compose 未安装"; exit 1)

echo ""
echo "9. 停止旧容器（如果存在）..."
docker-compose down 2>/dev/null || true

echo ""
echo "10. 启动 Docker Compose..."
docker-compose up -d --build

echo ""
echo "11. 等待服务启动..."
sleep 30

echo ""
echo "12. 检查容器状态..."
docker-compose ps

echo ""
echo "13. 查看后端日志..."
docker-compose logs backend --tail=50

echo ""
echo "14. 检查健康状态..."
curl -s http://localhost:8000/health || echo "健康检查失败"

echo ""
echo "=== 部署完成 ==="
echo "前端访问地址: http://$SERVER_IP"
echo "后端API地址: http://$SERVER_IP/api"
echo "健康检查: http://$SERVER_IP/api/health"
echo ""
echo "如果 API 返回 502，请检查:"
echo "1. 后端容器是否正常运行: docker-compose ps"
echo "2. 后端日志是否有错误: docker-compose logs backend"
