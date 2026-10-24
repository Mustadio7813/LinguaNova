"""One coordinator owns all bounded tasks and invalidates late work."""
import asyncio
import threading


class CancelledJob(Exception):
    pass


class WorkQueue:
    def __init__(self, concurrency=2, cancelled=None):
        self.cancelled=cancelled or threading.Event()
        self.limit=asyncio.Semaphore(max(1,min(int(concurrency),8)))

    def check(self):
        if self.cancelled.is_set():
            raise CancelledJob('Job cancelled; late responses discarded')

    async def call(self, operation, *args, timeout=90):
        self.check()
        async with self.limit:
            task=asyncio.create_task(operation(*args))
            try:
                deadline=asyncio.get_running_loop().time()+timeout
                while not task.done():
                    self.check()
                    if asyncio.get_running_loop().time()>=deadline:
                        raise TimeoutError('Task deadline exceeded')
                    await asyncio.wait([task],timeout=.1)
                self.check()
                return await task
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task,return_exceptions=True)
