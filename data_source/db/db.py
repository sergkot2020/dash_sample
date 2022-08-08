import logging
from typing import List
from time import monotonic
from data_source.db.postgres import PostgresDB

logger = logging.getLogger(__name__)


class DataBase(PostgresDB):
    def __init__(self, name, **kwargs):
        super().__init__(name, timezone='UTC', **kwargs)

    async def pool_close(self):
        await self.pool.close()

    async def sync_tickers(self, tickers: List[str]) -> dict:
        logger.info(f'Start to sync tickers')

        t1 = monotonic()

        ticker_map = {}

        rowset = await self.pool.fetch(
            '''\
select id, ticker
from ticker
''',
        )

        ticker_need_add = []
        ticker_need_del = []
        tickers_exists = []

        for ticker_id, ticker in rowset:
            tickers_exists.append(ticker)
            if ticker not in tickers:
                ticker_need_del.append(ticker_id)
                continue

            ticker_map[ticker] = ticker_id

        for ticker in tickers:
            if ticker not in tickers_exists:
                ticker_need_add.append((ticker,))

        if ticker_need_del:
            await self.pool.execute(
                '''\
delete from ticker
where id = any($1)
''',
                ticker_need_del,
            )

        if ticker_need_add:
            await self.pool.executemany(
                '''\
insert into ticker (ticker)
values ($1)
''',
                ticker_need_add,
            )

        if ticker_need_add:
            rowset = await self.pool.fetch(
                '''\
select id, ticker
from ticker
'''
            )
            ticker_map = {ticker: _id for _id, ticker in rowset}

        t2 = monotonic()
        logger.info(f'Done sync {t2 - t1} sec.')

        return ticker_map

    async def save_tick(self, data: list):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    '''\
create temporary table if not exists  temp_ticker_log
(
    ticker_id integer not null,
    price     numeric not null
)
with (fillfactor=100, oids=false)
on commit delete rows
''',
                )
                await conn.copy_records_to_table(
                    'temp_ticker_log',
                    records=data,
                )
                await conn.execute(
                    '''\
insert into ticker_log (ticker_id, price)
select 
    ticker_id,
    price
from temp_ticker_log
''',
                )



