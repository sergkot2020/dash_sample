__all__ = ['App']

import asyncio
import datetime
import logging
import typing
from typing import List
from datetime import datetime, timezone
from collections import deque, defaultdict
from random import random
from data_source.db import DataBase
from time import monotonic

logger = logging.getLogger(__name__)


def generate_movement():
    movement = -1 if random() < 0.5 else 1
    return movement


def price_generator():
    while True:
        yield generate_movement()


def utc_now():
    return datetime.now().replace(tzinfo=timezone.utc)


class App:
    def __init__(
            self,
            *,
            name: str,
            ticker_range: List[int],
            db_config: dict,
            data_generating_interval: int,
    ):
        self.name = name
        self.db_pool_size = db_config.pop('db_pool_size')
        self.tickers = [f'ticker_{n}' for n in range(*ticker_range)]
        self.gen_interval = data_generating_interval

        self.db = DataBase(name, **db_config)
        self.stopping = asyncio.Event()
        self.stopped = asyncio.Event()
        self.ticker_map = {}
        self.ticker_price = {}
        self.tasks = []

        self.scheduled_tasks = [
            self.generate_data
        ]

    def stop(self):
        self.stopping.set()

    async def wait_stopped(self):
        await self.stopped.wait()

    async def run(self):
        import sys
        logger.info('===============')
        logger.info(sys.path)
        await self.db.create_conn_pool(max_size=self.db_pool_size)

        self.ticker_map = await self.db.sync_tickers(self.tickers)
        self.ticker_price = {
            ticker: 0 for ticker in self.ticker_map.keys()
        }

        self.tasks.extend([
            asyncio.create_task(self._create_task(task()))
            for task in self.scheduled_tasks
        ])

        await self.stopping.wait()

        await self.db.pool_close()

        for task in self.tasks:
            task.cancel()

        self.stopped.set()

    async def _create_task(self, task):
        try:
            if isinstance(task, typing.Coroutine):
                return await task
            return await task()
        except asyncio.CancelledError:
            raise
        except:
            logger.error(f'Error in {task.__name__}')
            self.stop()

    async def generate_data(self):
        next_loop = monotonic() + self.gen_interval
        while True:
            t1 = monotonic()
            # m1 = utc_now().replace(second=0, microsecond=0)

            log_data = []
            for ticker in self.tickers:
                new_price = self.ticker_price[ticker] + generate_movement()
                log_data.append((self.ticker_map[ticker], new_price))
                self.ticker_price[ticker] = new_price

            await self.db.save_tick(log_data)
            t2 = monotonic()
            logger.debug(f'Save {len(self.tickers)} prices , {t2 - t1} sec')

            if next_loop > t1:
                delay = next_loop - t1
                next_loop += self.gen_interval
                logger.debug(f'Sleep: {delay}sec')
                await asyncio.sleep(delay)
            else:
                next_loop = t1 + self.gen_interval
                await asyncio.sleep(0)
