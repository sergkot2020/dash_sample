__all__ = ['App']

import asyncio
import logging
import typing
from datetime import timedelta
from time import monotonic
from typing import List
from collections import defaultdict
from data_source.db import DataBase
from utils.helpers import generate_movement, get_partition_info, utc_now

logger = logging.getLogger(__name__)


class App:
    def __init__(
            self,
            *,
            name: str,
            ticker_range: List[int],
            db_config: dict,
            insert_interval: int,
            generate_historical_data: bool,
            historical_timedelta: int,
    ):
        self.name = name
        self.generate_historical_data = generate_historical_data
        self.historical_timedelta = historical_timedelta
        self.db_pool_size = db_config.pop('db_pool_size')
        self.tickers = [f'ticker_{n}' for n in range(*ticker_range)]
        self.insert_interval = insert_interval

        self.db = DataBase(name, **db_config)
        self.stopping = asyncio.Event()
        self.stopped = asyncio.Event()
        self.ticker_map = {}
        self.ticker_price = {}
        self.tasks = []

        self.scheduled_tasks = [
            self.insert_data,
            self.drop_old_partition,
        ]

    def stop(self):
        self.stopping.set()

    async def wait_stopped(self):
        await self.stopped.wait()

    async def run(self):
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

    async def insert_data(self):
        if self.generate_historical_data:
            await self.insert_historical_data()

        next_loop = monotonic() + self.insert_interval
        while True:
            t1 = monotonic()
            now = utc_now()
            log_data = []
            for ticker in self.tickers:
                new_price = self.ticker_price[ticker] + generate_movement()
                log_data.append((self.ticker_map[ticker], new_price, now))
                self.ticker_price[ticker] = new_price

            tab_name, ts_constraint_start, ts_constraint_end = get_partition_info(now)
            await self.db.save_tick(
                data=log_data,
                tab_name=tab_name,
                ts_constraint_start=ts_constraint_start,
                ts_constraint_end=ts_constraint_end,
            )

            t2 = monotonic()
            logger.debug(f'Save {len(self.tickers)} prices , {t2 - t1} sec')

            if next_loop > t1:
                delay = next_loop - t1
                next_loop += self.insert_interval
                logger.debug(f'Sleep: {delay}sec')
                await asyncio.sleep(delay)
            else:
                next_loop = t1 + self.insert_interval
                await asyncio.sleep(0)

    async def insert_historical_data(self):
        logger.info('Start to insert daily data')
        t1 = monotonic()

        now = utc_now()
        start = (now - timedelta(hours=self.historical_timedelta)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now

        rowset = await self.db.get_intervals(start, end)

        data = defaultdict(list)
        constraints = defaultdict(dict)
        for i, row in enumerate(rowset):
            ts = row['ts']
            tab_name, ts_constraint_start, ts_constraint_end = get_partition_info(ts)
            constraints[tab_name]['ts_constraint_start'] = ts_constraint_start
            constraints[tab_name]['ts_constraint_end'] = ts_constraint_end

            if i % 3600 == 0:
                logger.info(f'Calc ts -> {ts}')

            for ticker in self.tickers:
                new_price = self.ticker_price[ticker] + generate_movement()
                data[tab_name].append((self.ticker_map[ticker], new_price, ts))
                self.ticker_price[ticker] = new_price

        for tab_name, log_data in data.items():
            ts_constraint_start = constraints[tab_name]['ts_constraint_start']
            ts_constraint_end = constraints[tab_name]['ts_constraint_end']
            await self.db.save_tick(
                data=log_data,
                tab_name=tab_name,
                ts_constraint_start=ts_constraint_start,
                ts_constraint_end=ts_constraint_end,
            )
            logger.info(f'Insert data into {tab_name}')

        t2 = monotonic()
        logger.info(f'Insert daily data: {t2 - t1}')

    async def drop_old_partition(self):
        pass
