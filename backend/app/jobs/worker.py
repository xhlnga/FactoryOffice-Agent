import argparse
import logging
import time
from collections.abc import Callable, Sequence
from typing import Any

from app.core.config import settings

try:  # pragma: no cover - 依赖是否安装由运行环境决定，业务测试不强依赖 Redis。
    from redis import Redis
    from rq import Queue, Retry, Worker
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]
    Queue = None  # type: ignore[assignment]
    Retry = None  # type: ignore[assignment]
    Worker = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


def get_redis_connection():
    """创建 Redis 连接；未安装依赖时给出清晰错误。"""
    if Redis is None:
        raise RuntimeError("缺少 redis/rq 依赖，请先安装 backend/requirements.txt。")
    return Redis.from_url(settings.redis_url)


def get_queue(name: str | None = None):
    """获取 RQ 队列。"""
    if Queue is None:
        raise RuntimeError("缺少 rq 依赖，请先安装 backend/requirements.txt。")
    return Queue(name or settings.job_queue_name, connection=get_redis_connection())


def enqueue_job(
    func: Callable[..., Any],
    *args: Any,
    queue_name: str | None = None,
    job_id: str | None = None,
    retry: bool = True,
    **kwargs: Any,
):
    """统一入队入口。

    企业集成任务通常是外部 I/O，失败需要自动重试；本地调用仍可直接执行具体 job 函数。
    """
    queue = get_queue(queue_name)
    retry_policy = None
    if retry and Retry is not None and settings.job_max_retries > 0:
        retry_policy = Retry(
            max=settings.job_max_retries,
            interval=settings.job_retry_intervals_seconds,
        )
    return queue.enqueue(func, *args, kwargs=kwargs, job_id=job_id, retry=retry_policy)


def run_worker(queue_names: Sequence[str] | None = None, *, with_scheduler: bool = False) -> None:
    """启动 RQ worker。"""
    if Worker is None:
        raise RuntimeError("缺少 rq 依赖，请先安装 backend/requirements.txt。")
    connection = get_redis_connection()
    queues = list(queue_names or [settings.job_queue_name])
    logger.info("启动后台 worker，queues=%s", queues)
    Worker(queues, connection=connection).work(with_scheduler=with_scheduler)


def enqueue_periodic_jobs() -> dict[str, str]:
    """周期性把扫描任务放入队列。

    真实项目可换成专门调度器；这里用轻量循环保持 Docker Compose 可直接运行。
    """
    from app.jobs.business_sync_jobs import scan_failed_business_sync_records
    from app.jobs.cleanup_jobs import cleanup_old_integration_events, cleanup_old_notification_deliveries
    from app.jobs.notification_jobs import scan_retryable_notifications
    from app.jobs.org_sync_jobs import scan_active_org_sync_configs
    from app.jobs.sla_jobs import scan_active_sla_instances

    bucket = int(time.time() // settings.job_scheduler_interval_seconds)
    jobs = {
        "notifications": enqueue_job(
            scan_retryable_notifications,
            job_id=f"periodic:notifications:{bucket}",
            limit=settings.job_batch_size,
        ).id,
        "business_sync": enqueue_job(
            scan_failed_business_sync_records,
            job_id=f"periodic:business-sync:{bucket}",
            limit=settings.job_batch_size,
        ).id,
        "org_sync": enqueue_job(
            scan_active_org_sync_configs,
            job_id=f"periodic:org-sync:{bucket}",
            limit=settings.job_batch_size,
        ).id,
        "sla": enqueue_job(
            scan_active_sla_instances,
            job_id=f"periodic:sla:{bucket}",
            limit=settings.job_batch_size,
        ).id,
        "cleanup_events": enqueue_job(
            cleanup_old_integration_events,
            job_id=f"periodic:cleanup-events:{bucket}",
            retry=False,
        ).id,
        "cleanup_notifications": enqueue_job(
            cleanup_old_notification_deliveries,
            job_id=f"periodic:cleanup-notifications:{bucket}",
            retry=False,
        ).id,
    }
    logger.info("周期任务已入队：%s", jobs)
    return jobs


def run_scheduler_loop() -> None:
    """启动轻量调度循环。"""
    logger.info("启动后台 scheduler，interval=%s seconds", settings.job_scheduler_interval_seconds)
    while True:
        try:
            enqueue_periodic_jobs()
        except Exception:  # noqa: BLE001 - 调度器不能因为单次入队失败退出。
            logger.exception("周期任务入队失败")
        time.sleep(settings.job_scheduler_interval_seconds)


def main() -> None:
    """命令行入口。"""
    logging.basicConfig(level=settings.log_level)
    parser = argparse.ArgumentParser(description="FactoryOffice-Agent 后台任务进程")
    subparsers = parser.add_subparsers(dest="command", required=True)

    worker_parser = subparsers.add_parser("worker", help="启动 RQ worker")
    worker_parser.add_argument("--queue", action="append", dest="queues", help="指定队列名，可重复传入")
    worker_parser.add_argument("--with-scheduler", action="store_true", help="启用 RQ 内置 scheduler")

    subparsers.add_parser("scheduler", help="启动轻量周期调度器")

    args = parser.parse_args()
    if args.command == "worker":
        run_worker(args.queues, with_scheduler=args.with_scheduler)
    elif args.command == "scheduler":
        run_scheduler_loop()


if __name__ == "__main__":
    main()

