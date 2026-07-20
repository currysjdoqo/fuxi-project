#!/bin/bash

echo "=== 习题库管理系统部署脚本 ==="

if [ -z "$1" ]; then
    echo "用法: $0 <服务器IP>"
    exit 1
fi

SERVER_IP="$1"
REMOTE_USER="root"
REMOTE_DIR="/opt/fuxi"

echo "1. 创建远程目录..."
ssh "$REMOTE_USER@$SERVER_IP" "mkdir -p $REMOTE_DIR"

echo "2. 上传项目文件..."
rsync -av --exclude='.git' --exclude='node_modules' --exclude='dist' \
      --exclude='data' --exclude='uploads' --exclude='.env' \
      --exclude='__pycache__' --exclude='*.pyc' \
      . "$REMOTE_USER@$SERVER_IP:$REMOTE_DIR/"

echo "3. 创建数据目录..."
ssh "$REMOTE_USER@$SERVER_IP" "mkdir -p $REMOTE_DIR/data $REMOTE_DIR/uploads"

echo "4. 设置权限..."
ssh "$REMOTE_USER@$SERVER_IP" "chown -R www-data:www-data $REMOTE_DIR/data $REMOTE_DIR/uploads"

echo "5. 启动 Docker Compose..."
ssh "$REMOTE_USER@$SERVER_IP" "cd $REMOTE_DIR && docker-compose up -d --build"

echo "6. 等待服务启动..."
sleep 10

echo "7. 检查容器状态..."
ssh "$REMOTE_USER@$SERVER_IP" "docker-compose ps"

echo ""
echo "=== 部署完成 ==="
echo "前端访问地址: http://$SERVER_IP"
echo "后端API地址: http://$SERVER_IP/api"
echo "健康检查: http://$SERVER_IP/api/health"
