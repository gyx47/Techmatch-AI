#!/usr/bin/env python3
"""
前端启动脚本
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    """启动Vue3前端服务"""
    # 切换到frontend目录
    frontend_dir = Path(__file__).parent / "frontend"
    os.chdir(frontend_dir)
    
    # 检查Node.js环境
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("错误: 未找到Node.js，请先安装Node.js")
            sys.exit(1)
        print(f"Node.js版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("错误: 未找到Node.js，请先安装Node.js")
        sys.exit(1)
    
    # 检查npm（Windows 需解析 npm.cmd）
    try:
        npm_cmd = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm_cmd:
            print("错误: 未找到npm")
            sys.exit(1)
        result = subprocess.run([npm_cmd, "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("错误: 未找到npm")
            sys.exit(1)
        print(f"npm版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("错误: 未找到npm")
        sys.exit(1)
    
    # 安装依赖
    print("正在安装前端依赖...")
    try:
        subprocess.run([npm_cmd, "install"], check=True)
    except subprocess.CalledProcessError:
        print("依赖安装失败，请手动运行: cd frontend && npm install")
        sys.exit(1)
    
    # 启动开发服务器
    print("启动Vue3开发服务器...")
    print("前端地址: http://localhost:5173")
    print("按 Ctrl+C 停止服务")
    
    try:
        subprocess.run([npm_cmd, "run", "dev"])
    except KeyboardInterrupt:
        print("\n服务已停止")

if __name__ == "__main__":
    main()
