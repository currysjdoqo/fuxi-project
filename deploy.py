import paramiko
import os
import zipfile
from dotenv import load_dotenv

load_dotenv()

SERVER_IP = os.getenv("DEPLOY_SERVER_IP")
USERNAME = os.getenv("DEPLOY_USERNAME")
PASSWORD = os.getenv("DEPLOY_PASSWORD")

if not SERVER_IP or not USERNAME or not PASSWORD:
    raise EnvironmentError("请在 .env 文件中配置 DEPLOY_SERVER_IP, DEPLOY_USERNAME, DEPLOY_PASSWORD")

EXCLUDE_DIRS = {'node_modules', 'dist', '.git', '.trae', '__pycache__', 'data', 'uploads', '.venv', '.pytest_cache'}
EXCLUDE_FILES = {'.env', '.gitignore', 'node.msi', 'test.db', 'exercise.db', 'create_package.py', 'create_package.ps1', 'deploy.py', 'deploy.sh', 'DEPLOY_MANUAL.md', 'fuxi-deploy.zip'}

def create_deploy_package():
    package_name = 'fuxi-deploy.zip'
    
    if os.path.exists(package_name):
        os.remove(package_name)
    
    print(f'创建部署包: {package_name}')
    count = 0
    
    with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if file in EXCLUDE_FILES or file.endswith('.pyc') or file.endswith('.pyo'):
                    continue
                
                local_path = os.path.join(root, file)
                arcname = os.path.relpath(local_path, '.')
                
                zf.write(local_path, arcname)
                count += 1
                print(f'  添加: {arcname}')
    
    size = os.path.getsize(package_name) / 1024
    print(f'\n部署包已创建: {package_name} ({count} 个文件, {int(size)} KB)')
    return package_name

def execute_command(ssh, command):
    print(f"\n执行命令: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    stdout_text = stdout.read().decode()
    stderr_text = stderr.read().decode()
    if stdout_text:
        print("输出:", stdout_text)
    if stderr_text:
        print("错误:", stderr_text)
    return stdout_text, stderr_text

def main():
    print("=== 步骤1: 创建部署包 ===")
    package_name = create_deploy_package()
    
    print("\n=== 步骤2: 连接服务器 ===")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        transport = paramiko.Transport((SERVER_IP, 22))
        transport.banner_timeout = 60
        transport.connect(username=USERNAME, password=PASSWORD)
        
        ssh._transport = transport
        
        print("SSH连接成功!")
        
        print("\n=== 步骤3: 上传部署包 ===")
        sftp = ssh.open_sftp()
        sftp.put(package_name, f"/opt/fuxi/fuxi-deploy.zip")
        sftp.close()
        print(f"部署包已上传")
        
        print("\n=== 步骤4: 停止旧容器 ===")
        execute_command(ssh, "docker stop fuxi-backend fuxi-frontend 2>/dev/null || true")
        execute_command(ssh, "docker rm fuxi-backend fuxi-frontend 2>/dev/null || true")
        
        print("\n=== 步骤5: 解压部署包 ===")
        execute_command(ssh, f"cd /opt/fuxi && unzip -o fuxi-deploy.zip")
        
        print("\n=== 步骤6: 重建并启动容器 ===")
        execute_command(ssh, f"cd /opt/fuxi && docker build -t fuxi-backend .")
        
        env_vars = f"ALLOWED_ORIGINS=http://{SERVER_IP},http://{SERVER_IP}:80,http://localhost:80,http://localhost"
        execute_command(ssh, f"cd /opt/fuxi && docker run -d --name fuxi-backend --network fuxi-network -p 8000:8000 -e '{env_vars}' -v /opt/fuxi/data:/app/data -v /opt/fuxi/uploads:/app/uploads --restart unless-stopped fuxi-backend")
        execute_command(ssh, f"cd /opt/fuxi && docker run -d --name fuxi-frontend --network fuxi-network -p 80:80 --restart unless-stopped fuxi-frontend")
        
        print("\n=== 步骤7: 等待服务启动 ===")
        import time
        time.sleep(30)
        
        print("\n=== 步骤8: 检查容器状态 ===")
        execute_command(ssh, "docker ps")
        
        print("\n=== 步骤9: 测试API ===")
        execute_command(ssh, "curl -s http://localhost:8000/health")
        execute_command(ssh, "curl -s http://localhost/api/auth/register -X POST -H 'Content-Type: application/json' -d '{\"username\":\"securetest\",\"password\":\"123456\"}'")
        execute_command(ssh, "curl -s http://localhost/api/auth/login -X POST -H 'Content-Type: application/json' -d '{\"username\":\"securetest\",\"password\":\"123456\"}'")
        
        ssh.close()
        print("\n=== 安全修复部署完成 ===")
        
    except Exception as e:
        print(f"\n部署失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
