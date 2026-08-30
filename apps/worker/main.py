"""
后台任务 worker
轮询 tasks 表认领任务并执行，复用现有 service 层逻辑

启动方式（项目根目录）：
    python -m apps.worker.main
"""

import logging
import signal
import time
from typing import Any, Dict

from apps.api.services import task_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("worker")

POLL_INTERVAL_SECONDS = 2

_shutdown = False


def _handle_annual_report(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    from apps.api.services.user_service import get_user_bazi
    from apps.api.services.fortune_report_service import fortune_report_service

    year = payload["year"]
    user_bazi = get_user_bazi(user_id)
    return fortune_report_service.generate_annual_report(user_id, user_bazi, year)


def _handle_wardrobe_report(user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    from apps.api.services.wardrobe_report_service import wardrobe_report_service

    year = payload["year"]
    try:
        return wardrobe_report_service.generate_report(user_id, year)
    except Exception:
        # 行停留在 pending 会让用户以为还在生成，显式标记失败（重试成功后会被覆盖）
        wardrobe_report_service.mark_failed(user_id, year)
        raise


HANDLERS = {
    "annual_report": _handle_annual_report,
    "wardrobe_report": _handle_wardrobe_report,
}


def _request_shutdown(signum, frame):
    global _shutdown
    _shutdown = True
    logger.info("收到退出信号，处理完当前任务后退出")


def run_once() -> bool:
    """认领并执行一个任务。返回是否处理了任务"""
    task = task_service.claim_task()
    if not task:
        return False

    task_id = task["id"]
    task_type = task["task_type"]
    logger.info(f"开始执行任务 {task_type} id={task_id} user={task['user_id']}")

    handler = HANDLERS.get(task_type)
    if handler is None:
        task_service.mark_failed(task_id, f"未知任务类型: {task_type}", retries=task_service.MAX_RETRIES)
        return True

    try:
        result = handler(task["user_id"], task["payload"] or {})
        task_service.mark_done(task_id, result)
    except Exception as e:
        logger.exception(f"任务执行异常 id={task_id}")
        task_service.mark_failed(task_id, str(e), retries=task.get("retries", 0))
    return True


def main():
    signal.signal(signal.SIGINT, _request_shutdown)
    signal.signal(signal.SIGTERM, _request_shutdown)
    logger.info(f"Worker 已启动，支持任务类型: {list(HANDLERS)}")

    while not _shutdown:
        try:
            handled = run_once()
        except Exception:
            logger.exception("worker 循环异常")
            handled = False
        if not handled and not _shutdown:
            time.sleep(POLL_INTERVAL_SECONDS)

    logger.info("Worker 已退出")


if __name__ == "__main__":
    main()
