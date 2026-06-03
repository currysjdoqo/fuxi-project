import subprocess
import os
import sys
import time
import platform
import signal
import socket

def is_port_in_use(port):
    """检查端口是否被占用"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(('localhost', port)) == 0
    except Exception:
        return False

def find_available_port(start_port=5173, max_port=5200):
    """查找可用端口"""
    for port in range(start_port, max_port + 1):
        if not is_port_in_use(port):
            return port
    return None

def run_command(cmd, cwd=None):
    """运行命令并返回进程对象"""
    print(f"Executing: {cmd}")
    if platform.system() == 'Windows':
        # 使用 shell=True 但不创建新窗口
        return subprocess.Popen(
            cmd, 
            cwd=cwd, 
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    else:
        return subprocess.Popen(
            cmd, 
            cwd=cwd, 
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

def read_process_output(proc, name):
    """读取进程输出（后台线程）"""
    def read_output():
        while proc.poll() is None:
            try:
                line = proc.stdout.readline()
                if line:
                    print(f"[{name}] {line.strip()}")
            except Exception:
                pass
    threading.Thread(target=read_output, daemon=True).start()

def start_backend(backend_dir):
    """启动后端服务"""
    print("\n[INFO] Starting backend service...")
    
    # 检查端口
    if is_port_in_use(8000):
        print("[ERROR] Port 8000 is already in use!")
        return None
    
    # 检查虚拟环境
    activate_script = os.path.join(backend_dir, '.venv', 'Scripts', 'activate')
    if not os.path.exists(activate_script):
        print(f"[ERROR] Virtual environment not found at {activate_script}")
        return None
    
    cmd = f'"{activate_script}" && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload'
    proc = run_command(cmd, cwd=backend_dir)
    
    # 等待启动
    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(8000):
            print("[INFO] Backend service started successfully!")
            return proc
        time.sleep(0.5)
        if proc.poll() is not None:
            # 进程已退出，检查错误
            output = proc.stdout.read() if proc.stdout else ""
            print(f"[ERROR] Backend failed to start: {output}")
            return None
    
    print("[ERROR] Backend service startup timed out!")
    proc.kill()
    return None

def start_frontend(frontend_dir):
    """启动前端服务"""
    print("\n[INFO] Starting frontend service...")
    
    # 查找可用端口
    frontend_port = find_available_port(5173)
    if frontend_port is None:
        print("[ERROR] No available port found for frontend!")
        return None, None
    
    # 检查 npm 是否可用
    npm_path = os.path.join(frontend_dir, 'node_modules', '.bin', 'npm.cmd')
    if os.path.exists(npm_path):
        cmd = f'"{npm_path}" run dev -- --host 127.0.0.1 --port {frontend_port}'
    else:
        cmd = f'npm run dev -- --host 127.0.0.1 --port {frontend_port}'
    
    proc = run_command(cmd, cwd=frontend_dir)
    
    # 等待启动
    timeout = 15
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(frontend_port):
            print(f"[INFO] Frontend service started successfully on port {frontend_port}!")
            return proc, frontend_port
        time.sleep(0.5)
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            print(f"[ERROR] Frontend failed to start: {output}")
            return None, None
    
    print("[ERROR] Frontend service startup timed out!")
    proc.kill()
    return None, None

def check_dependencies():
    """检查必要依赖"""
    print("[INFO] Checking dependencies...")
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查Python虚拟环境
    venv_dir = os.path.join(backend_dir, '.venv')
    if not os.path.exists(venv_dir):
        print("[ERROR] Virtual environment not found at:", venv_dir)
        print("Please run: python -m venv .venv")
        return False
    
    # 检查前端依赖
    frontend_dir = os.path.join(backend_dir, 'frontend')
    node_modules_dir = os.path.join(frontend_dir, 'node_modules')
    if not os.path.exists(node_modules_dir):
        print("[ERROR] Frontend dependencies not installed at:", node_modules_dir)
        print("Please run 'npm install' in frontend directory.")
        return False
    
    # 检查 main.py
    main_file = os.path.join(backend_dir, 'main.py')
    if not os.path.exists(main_file):
        print("[ERROR] main.py not found at:", main_file)
        return False
    
    # 检查 package.json
    package_json = os.path.join(frontend_dir, 'package.json')
    if not os.path.exists(package_json):
        print("[ERROR] package.json not found at:", package_json)
        return False
    
    print("[INFO] All dependencies checked successfully!")
    return True

def stop_process(proc, name):
    """优雅停止进程"""
    if proc is None or proc.poll() is not None:
        return
    
    print(f"\n[INFO] Stopping {name} service...")
    
    try:
        if platform.system() == 'Windows':
            # Windows 上使用 taskkill
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        
        # 等待进程结束
        try:
            proc.wait(timeout=5)
            print(f"[INFO] {name} service stopped gracefully")
        except subprocess.TimeoutExpired:
            print(f"[WARNING] {name} service did not stop in time, forcing kill...")
            proc.kill()
            proc.wait()
            print(f"[INFO] {name} service killed")
            
    except Exception as e:
        print(f"[ERROR] Failed to stop {name} service: {e}")
        try:
            proc.kill()
        except:
            pass

def main():
    print("="*60)
    print("    Exercise Management System - One-Click Launch")
    print("="*60)
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查依赖
    if not check_dependencies():
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    backend_proc = None
    frontend_proc = None
    frontend_port = None
    
    try:
        # 启动后端
        backend_proc = start_backend(backend_dir)
        if backend_proc is None:
            print("[ERROR] Failed to start backend service")
            return
        
        # 启动前端
        frontend_proc, frontend_port = start_frontend(os.path.join(backend_dir, 'frontend'))
        if frontend_proc is None:
            print("[ERROR] Failed to start frontend service")
            return
        
        print("\n" + "="*60)
        print("✅ All services started successfully!")
        print(f"🌐 Backend: http://localhost:8000")
        print(f"🌐 Frontend: http://localhost:{frontend_port}")
        print("="*60)
        print("\nPress Ctrl+C to stop all services...")
        
        # 保持主进程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] User interrupted, stopping services...")
        
    finally:
        # 停止所有进程
        if frontend_proc:
            stop_process(frontend_proc, "Frontend")
        if backend_proc:
            stop_process(backend_proc, "Backend")
        
        print("\n[INFO] All services stopped. Goodbye!")

if __name__ == '__main__':
    import threading
    main()
