import asyncio
from contextlib import asynccontextmanager
from database.models import GenerationTask, User
from database.db import AsyncSessionLocal

class TaskQueue:
    def __init__(self, sd_client):
        self.sd_client = sd_client
        self.queue = asyncio.Queue()
        self.current_task = None
        self.progress_task = None

    async def add_task(self, user_id: int, params: dict) -> int:
        async with AsyncSessionLocal() as session:
            task = GenerationTask(
                user_id=user_id,
                params=params,
                status='queued'
            )
            session.add(task)
            await session.commit()
            await self.queue.put(task.id)
            return task.id

    async def process_tasks(self):
        while True:
            task_id = await self.queue.get()
            async with AsyncSessionLocal() as session:
                task = await session.get(GenerationTask, task_id)
                task.status = 'processing'
                await session.commit()
                
                try:
                    images = await self.sd_client.txt2img(**task.params)
                    task.result_images = [str(img) for img in images]  # Реальная реализация сохранения
                    task.status = 'completed'
                except Exception as e:
                    task.status = 'failed'
                finally:
                    await session.commit()
                    self.queue.task_done()

    async def start_progress_monitoring(self, bot):
        while True:
            if self.current_task:
                progress = await self.sd_client.get_progress()
                # Обновляем прогресс в БД и отправляем уведомления
                async with AsyncSessionLocal() as session:
                    task = await session.get(GenerationTask, self.current_task)
                    if task:
                        task.progress = progress.get('progress', 0.0)
                        await session.commit()
                        await bot.send_message(
                            chat_id=task.user.telegram_id,
                            text=f"Прогресс: {task.progress*100:.1f}%"
                        )
            await asyncio.sleep(1)