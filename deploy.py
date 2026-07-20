import paramiko
import os
import time

SERVER_IP = "43.108.18.169"
USERNAME = "root"
PASSWORD = "57r.fQPLq.Gm8j2"
REMOTE_DIR = "/opt/fuxi"

def main():
    print("=== 测试SSH连接 ===")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        transport = paramiko.Transport((SERVER_IP, 22))
        transport.banner_timeout = 60
        transport.connect(username=USERNAME, password=PASSWORD)
        
        ssh._transport = transport
        
        print("\nSSH连接成功!")
        
        stdin, stdout, stderr = ssh.exec_command("echo 'Hello from server'")
        print("服务器响应:", stdout.read().decode())
        
        stdin, stdout, stderr = ssh.exec_command("uname -a")
        print("服务器信息:", stdout.read().decode())
        
        ssh.close()
        print("\n测试完成!")
        
    except Exception as e:
        print(f"\n连接失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
