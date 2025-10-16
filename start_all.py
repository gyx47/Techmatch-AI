#!/usr/bin/env python3
"""
全栈启动脚本
"""
import os
import sys
import subprocess
import shutil
import threading
import time
from pathlib import Path

def start_backend():
    """启动后端服务"""
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print("启动后端服务...")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("后端服务已停止")

def start_frontend():
    """启动前端服务"""
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    print("启动前端服务...")
    try:
        # 解析 npm 可执行文件（Windows 使用 npm.cmd）
        npm_cmd = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm_cmd:
            print("错误: 未找到 npm，请确认已安装并加入 PATH")
            return
        subprocess.run([npm_cmd, "run", "dev"])
    except KeyboardInterrupt:
        print("前端服务已停止")

def main():
    """启动全栈服务"""
    print("AI论文搜索系统 - 全栈启动")
    print("=" * 50)
    
    # 检查环境
    print("检查环境...")
    
    # 检查Python
    if sys.version_info < (3, 8):
        print("错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 检查Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("错误: 未找到Node.js，请先安装Node.js")
            sys.exit(1)
    except FileNotFoundError:
        print("错误: 未找到Node.js，请先安装Node.js")
        sys.exit(1)
    
    # 解析 npm 可执行文件（Windows 需使用 npm.cmd）
    npm_cmd = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_cmd:
        print("错误: 未找到 npm，请确认已安装并加入 PATH")
        sys.exit(1)
    
    print("环境检查通过")
    print()
    
    # 安装后端依赖
    print("安装后端依赖...")
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    except subprocess.CalledProcessError:
        print("后端依赖安装失败")
        sys.exit(1)
    
    # 安装前端依赖
    print("安装前端依赖...")
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    try:
        subprocess.run([npm_cmd, "install"], check=True)
    except subprocess.CalledProcessError:
        print("前端依赖安装失败")
        sys.exit(1)
    
    print("依赖安装完成")
    print()
    
    # 启动服务
    print("启动服务...")
    print("后端地址: http://localhost:8000")
    print("前端地址: http://localhost:5173")
    print("API文档: http://localhost:8000/api/docs")
    print("按 Ctrl+C 停止所有服务")
    print("=" * 50)
    
    # 在新线程中启动后端
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # 等待后端启动
    time.sleep(3)
    
    # 启动前端（主线程）
    try:
        start_frontend()
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        print("服务已停止")

if __name__ == "__main__":
    main()
