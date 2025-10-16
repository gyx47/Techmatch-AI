"""
封装 arxiv_crawler 的启动与状态查询
"""
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional, Dict

_running_process: Optional[subprocess.Popen] = None
_last_task_params: Optional[Dict] = None

def start_crawler(date_from: str, date_until: str, keywords: Optional[list] = None, categories: Optional[list] = None) -> int:
    """在子进程中启动爬虫，返回进程PID"""
    global _running_process, _last_task_params

    if _running_process and _running_process.poll() is None:
        # 已有任务在运行
        return _running_process.pid

    project_root = Path(__file__).resolve().parents[1]
    crawler_script = project_root / "arxiv_crawler" / "arxiv_crawler.py"

    if not crawler_script.exists():
        raise FileNotFoundError("未找到 arxiv_crawler/arxiv_crawler.py")

    env = os.environ.copy()

    # 通过 python -c 方式传参（避免修改第三方脚本）
    py_code = (
        "import asyncio;"
        "from arxiv_crawler.arxiv_crawler import ArxivScraper;"
        f"scraper=ArxivScraper(date_from='{date_from}', date_until='{date_until}',"
        f" optional_keywords={keywords or ['LLM','GPT']},"
        f" category_whitelist={categories or ['cs.AI','cs.LG','cs.CL','cs.CV']});"
        "asyncio.run(scraper.fetch_all());"
        "scraper.to_markdown(meta=True)"
    )

    _running_process = subprocess.Popen(
        [sys.executable, "-c", py_code],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )

    _last_task_params = {
        "date_from": date_from,
        "date_until": date_until,
        "keywords": keywords,
        "categories": categories,
    }

    return _running_process.pid

def crawler_status() -> Dict:
    """返回当前爬虫任务状态"""
    global _running_process
    if _running_process is None:
        return {"running": False}
    code = _running_process.poll()
    return {
        "running": code is None,
        "returncode": code,
        "pid": _running_process.pid,
    }

def stop_crawler() -> bool:
    global _running_process
    if _running_process and _running_process.poll() is None:
        _running_process.terminate()
        return True
    return False


