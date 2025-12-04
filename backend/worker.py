"""
Redis/ARQ Worker 进程入口。

启动方式（在 backend 目录下）：
    cd backend
    arq worker.WorkerSettings
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

from arq.connections import RedisSettings

from api.routes.papers import core_generate_implementation_path

# 加载环境变量（和 main.py 一样的逻辑）
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if not env_file.exists():
    env_file = project_root / "env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Worker: 已加载环境变量文件: {env_file}")
else:
    print("Worker: 警告: 未找到 .env 文件，将使用系统环境变量")


async def task_wrapper_generate_path(
    ctx: Dict[str, Any],
    task_id: str,
    paper_ids: List[str],
    user_requirement: str,
    max_pages: int,
    user_id: int = None,
    history_id: int = None,
):
    """
    ARQ 任务包装器：调用核心实现路径生成逻辑，并把进度写入 Redis。
    """

    async def update_redis_progress(state: Dict[str, Any]):
        # 使用 task_id 作为进度 key
        redis = ctx["redis"]
        await redis.set(f"progress:{task_id}", json.dumps(state), ex=3600)

    return await core_generate_implementation_path(
        task_id=task_id,
        paper_ids=paper_ids,
        user_requirement=user_requirement,
        max_pages_per_paper=max_pages,
        update_progress_callback=update_redis_progress,
        user_id=user_id,
        history_id=history_id,
    )


class WorkerSettings:
    """
    ARQ Worker 配置。
    """

    redis_settings = RedisSettings(host="127.0.0.1", port=6379)
    functions = [task_wrapper_generate_path]



