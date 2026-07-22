import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time


IS_WINDOWS = platform.system() == "Windows"
BACKEND_PORT = 8000
FRONTEND_PORT_START = 5173
FRONTEND_PORT_END = 5200


def is_port_in_use(port):
    """Return True when the given localhost TCP port is occupied."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False


def find_available_port(start_port=FRONTEND_PORT_START, end_port=FRONTEND_PORT_END):
    """Find the first available port in the given range."""
    for port in range(start_port, end_port + 1):
        if not is_port_in_use(port):
            return port
    return None


def read_process_output(proc, name):
    """Stream child process output in a background thread."""

    def _reader():
        if proc.stdout is None:
            return
        for line in iter(proc.stdout.readline, ""):
            text = line.rstrip()
            if text:
                print(f"[{name}] {text}")
        proc.stdout.close()

    threading.Thread(target=_reader, daemon=True).start()


def run_command(cmd, cwd=None, name="Process"):
    """Start a child process with streamed output."""
    print(f"[INFO] Starting {name}: {cmd}")

    creationflags = 0
    if IS_WINDOWS:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    read_process_output(proc, name)
    return proc


def start_backend(project_dir):
    """Start the FastAPI backend."""
    print("\n[INFO] Starting backend service...")

    backend_port = BACKEND_PORT
    if is_port_in_use(backend_port):
        print(f"[WARNING] Port {BACKEND_PORT} is already in use, trying other ports...")
        for port in range(BACKEND_PORT + 1, BACKEND_PORT + 20):
            if not is_port_in_use(port):
                backend_port = port
                print(f"[INFO] Using port {backend_port} instead.")
                break
        else:
            print(f"[ERROR] No available port found in range {BACKEND_PORT+1}-{BACKEND_PORT+20}.")
            return None

    venv_python = os.path.join(project_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        print(f"[ERROR] Virtual environment Python not found: {venv_python}")
        return None

    cmd = f'"{venv_python}" -m uvicorn main:app --host 127.0.0.1 --port {backend_port} --reload'
    proc = run_command(cmd, cwd=project_dir, name="Backend")

    timeout = 10
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(BACKEND_PORT):
            print("[INFO] Backend service started successfully.")
            return proc
        if proc.poll() is not None:
            print(f"[ERROR] Backend exited early with code {proc.returncode}.")
            return None
        time.sleep(0.5)

    print("[ERROR] Backend service startup timed out.")
    stop_process(proc, "Backend")
    return None


def start_frontend(frontend_dir):
    """Start the Vite frontend."""
    print("\n[INFO] Starting frontend service...")

    frontend_port = find_available_port()
    if frontend_port is None:
        print("[ERROR] No available port found for frontend.")
        return None, None

    npm_cmd = shutil.which("npm")
    if npm_cmd is None:
        npm_cmd = os.path.join(frontend_dir, "node_modules", ".bin", "npm.cmd")
        if not os.path.exists(npm_cmd):
            print("[ERROR] npm was not found. Install Node.js and frontend dependencies first.")
            return None, None

    cmd = f'"{npm_cmd}" run dev -- --host 127.0.0.1 --port {frontend_port} --strictPort'
    proc = run_command(cmd, cwd=frontend_dir, name="Frontend")

    timeout = 15
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(frontend_port):
            print(f"[INFO] Frontend service started successfully on port {frontend_port}.")
            return proc, frontend_port
        if proc.poll() is not None:
            print(f"[ERROR] Frontend exited early with code {proc.returncode}.")
            return None, None
        time.sleep(0.5)

    print("[ERROR] Frontend service startup timed out.")
    stop_process(proc, "Frontend")
    return None, None


def check_dependencies(project_dir):
    """Check required project files and tools."""
    print("[INFO] Checking dependencies...")

    venv_python = os.path.join(project_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        print(f"[ERROR] Virtual environment not found: {venv_python}")
        print("Run: python -m venv .venv")
        return False

    frontend_dir = os.path.join(project_dir, "frontend")
    node_modules_dir = os.path.join(frontend_dir, "node_modules")
    if not os.path.exists(node_modules_dir):
        print(f"[ERROR] Frontend dependencies not installed: {node_modules_dir}")
        print("Run: cd frontend && npm install")
        return False

    main_file = os.path.join(project_dir, "main.py")
    if not os.path.exists(main_file):
        print(f"[ERROR] main.py not found: {main_file}")
        return False

    package_json = os.path.join(frontend_dir, "package.json")
    if not os.path.exists(package_json):
        print(f"[ERROR] package.json not found: {package_json}")
        return False

    print("[INFO] All dependencies checked successfully.")
    return True


def stop_process(proc, name):
    """Stop a child process as gracefully as possible."""
    if proc is None or proc.poll() is not None:
        return

    print(f"\n[INFO] Stopping {name} service...")
    try:
        if IS_WINDOWS:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()

        try:
            proc.wait(timeout=5)
            print(f"[INFO] {name} service stopped gracefully.")
        except subprocess.TimeoutExpired:
            print(f"[WARNING] {name} service did not stop in time, forcing kill...")
            proc.kill()
            proc.wait(timeout=5)
            print(f"[INFO] {name} service killed.")
    except Exception as exc:
        print(f"[ERROR] Failed to stop {name} service cleanly: {exc}")
        try:
            proc.kill()
            proc.wait(timeout=5)
            print(f"[INFO] {name} service killed.")
        except Exception:
            pass


def main():
    print("=" * 60)
    print("    Exercise Management System - One-Click Launch")
    print("=" * 60)

    project_dir = os.path.dirname(os.path.abspath(__file__))
    if not check_dependencies(project_dir):
        sys.exit(1)

    backend_proc = None
    frontend_proc = None

    try:
        backend_proc = start_backend(project_dir)
        if backend_proc is None:
            print("[ERROR] Failed to start backend service.")
            return

        frontend_proc, frontend_port = start_frontend(os.path.join(project_dir, "frontend"))
        if frontend_proc is None:
            print("[ERROR] Failed to start frontend service.")
            return

        print("\n" + "=" * 60)
        print("[OK] All services started successfully.")
        print(f"[URL] Backend:  http://127.0.0.1:{BACKEND_PORT}")
        print(f"[URL] Frontend: http://127.0.0.1:{frontend_port}")
        print("=" * 60)
        print("\nPress Ctrl+C to stop all services...")

        while True:
            if backend_proc.poll() is not None:
                print(f"\n[ERROR] Backend exited unexpectedly with code {backend_proc.returncode}.")
                break
            if frontend_proc.poll() is not None:
                print(f"\n[ERROR] Frontend exited unexpectedly with code {frontend_proc.returncode}.")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n[INFO] User interrupted, stopping services...")
    finally:
        stop_process(frontend_proc, "Frontend")
        stop_process(backend_proc, "Backend")
        print("\n[INFO] All services stopped. Goodbye!")


if __name__ == "__main__":
    main()
