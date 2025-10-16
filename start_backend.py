#!/usr/bin/env python3
"""
后端启动脚本
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    """启动FastAPI后端服务"""
    # 切换到backend目录
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # 检查Python环境
    if sys.version_info < (3, 8):
        print("错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    
    # 安装依赖
    print("正在安装依赖...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    except subprocess.CalledProcessError:
        print("依赖安装失败，请手动运行: pip install -r backend/requirements.txt")
        sys.exit(1)
    
    # 启动服务
    print("启动FastAPI服务器...")
    print("服务地址: http://localhost:8000")
    print("API文档: http://localhost:8000/api/docs")
    print("按 Ctrl+C 停止服务")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n服务已停止")

if __name__ == "__main__":
    main()
