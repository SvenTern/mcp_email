"""
Cron Scheduler — фоновый планировщик задач.

Функции:
- Проверка расписания каждую минуту
- Запуск задач по cron выражениям
- Управление параллельным выполнением
- Обработка file-watch триггеров
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable

from croniter import croniter

logger = logging.getLogger(__name__)


class CronScheduler:
    """
    Фоновый планировщик задач.

    Пример:
        scheduler = CronScheduler(db_path="/app/data/tasks.db")
        await scheduler.start()

        # Для остановки:
        await scheduler.stop()
    """

    def __init__(
        self,
        db_path: str,
        check_interval: int = 60,  # Интервал проверки в секундах
        max_concurrent: int = 5,    # Макс. параллельных задач
        task_executor: Optional[Callable[[str], Awaitable[dict]]] = None
    ):
        self.db_path = db_path
        self.check_interval = check_interval
        self.max_concurrent = max_concurrent
        self.task_executor = task_executor

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running_tasks: set[str] = set()  # task_ids currently running

    def set_task_executor(self, executor: Callable[[str], Awaitable[dict]]) -> None:
        """Установить функцию выполнения задач."""
        self.task_executor = executor

    async def start(self) -> None:
        """Запустить scheduler."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Cron Scheduler started")

    async def stop(self) -> None:
        """Остановить scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cron Scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Основной цикл scheduler."""
        while self._running:
            try:
                await self._check_and_run_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_and_run_tasks(self) -> None:
        """Проверить расписание и запустить задачи."""
        now = datetime.now(timezone.utc)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем все включённые задачи с расписанием
        cursor.execute("""
            SELECT * FROM tasks
            WHERE enabled = 1 AND schedule IS NOT NULL
        """)
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()

        for task in tasks:
            # Пропускаем уже выполняющиеся
            if task['id'] in self._running_tasks:
                continue

            # Проверяем, нужно ли запускать
            if self._should_run(task, now):
                # Запускаем в фоне с ограничением параллельности
                asyncio.create_task(self._run_task_with_semaphore(task['id']))

    def _should_run(self, task: dict, now: datetime) -> bool:
        """Проверить, должна ли задача запуститься."""
        try:
            schedule = task.get('schedule')
            if not schedule:
                return False

            # Получаем время последнего запуска
            last_run = self._get_last_run(task['id'])

            # Создаём croniter с базой от последнего запуска или начала минуты
            if last_run:
                base_time = last_run
            else:
                base_time = now.replace(second=0, microsecond=0)

            cron = croniter(schedule, base_time)

            # Получаем следующее время запуска
            next_run = cron.get_next(datetime)

            # Делаем next_run timezone-aware если нужно
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)

            # Если next_run <= now и после last_run — запускаем
            if next_run <= now:
                if last_run is None or next_run > last_run:
                    logger.info(f"Task '{task['name']}' scheduled to run (next_run={next_run}, now={now})")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking schedule for {task['name']}: {e}")
            return False

    def _get_last_run(self, task_id: str) -> Optional[datetime]:
        """Получить время последнего запуска задачи."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT started_at FROM history
            WHERE task_id = ?
            ORDER BY started_at DESC
            LIMIT 1
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            try:
                dt = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None
        return None

    async def _run_task_with_semaphore(self, task_id: str) -> None:
        """Запустить задачу с ограничением параллельности."""
        async with self._semaphore:
            self._running_tasks.add(task_id)
            try:
                if self.task_executor:
                    await self.task_executor(task_id)
                else:
                    logger.warning(f"No task executor set, skipping task {task_id}")
            except Exception as e:
                logger.error(f"Task execution error {task_id}: {e}")
            finally:
                self._running_tasks.discard(task_id)

    def get_running_tasks(self) -> set[str]:
        """Получить список выполняющихся задач."""
        return self._running_tasks.copy()

    def is_running(self) -> bool:
        """Проверить, запущен ли scheduler."""
        return self._running


# Глобальный экземпляр scheduler
_scheduler: Optional[CronScheduler] = None


def get_scheduler() -> Optional[CronScheduler]:
    """Получить глобальный scheduler."""
    return _scheduler


async def start_scheduler(
    db_path: str,
    task_executor: Optional[Callable[[str], Awaitable[dict]]] = None
) -> CronScheduler:
    """Запустить глобальный scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler(db_path=db_path, task_executor=task_executor)
        await _scheduler.start()
    return _scheduler


async def stop_scheduler() -> None:
    """Остановить глобальный scheduler."""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None
