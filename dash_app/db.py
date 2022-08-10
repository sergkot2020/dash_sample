from datetime import datetime
from functools import lru_cache
from typing import List

import psycopg2


class DataSource:
    def __init__(
            self,
            *,
            schema,
            host,
            port,
            database,
            user,
            password,
    ):
        self.params = {
            'dbname': database,
            'user': user,
            'password': password,
            'host': host,
            'port': port,
        }
        self.schema = schema,
        self.conn = psycopg2.connect(**self.params)
        self.execute("set timezone to 'UTC'")

    def select(self, query: str) -> List[tuple]:
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def execute(self, query):
        with self.conn.cursor() as cursor:
            cursor.execute(query)

    def get_tickers(self):
        return self.select(
            '''\
select ticker, id
from data_source.ticker
''',
        )

    def get_update(self, ticker_id: int, ts: datetime, limit=60):
        return self.select(
            f'''\
select
    price,
    created
from data_source.ticker_log
where ticker_id = {ticker_id}
    and date_trunc('second', created) > '{ts:%Y-%m-%d %H:%M:%S}'::timestamptz
order by created
limit {limit}
''',
        )

    @lru_cache(maxsize=128, typed=True)
    def get_data_by_range(self, ticker_id: int, start: datetime, end: datetime):
        return self.select(
            f'''\
select
    price,
    created 
from data_source.ticker_log_part
where ticker_id = {ticker_id}
    and created > '{start:%Y-%m-%d %H:%M:%S}'::timestamptz
    and created < '{end:%Y-%m-%d %H:%M:%S}'::timestamptz
order by created
''',
        )

    def get_last_data(self, ticker_id: int, limit=300):
        rowset = self.select(
            f'''\
select 
    price, 
    created
from data_source.ticker_log_part
where ticker_id = {ticker_id}
order by created desc
limit {limit}
''',
        )
        return sorted(rowset, key=lambda r: r[1])

    def get_date_range(self, ticker_id, limit=24):
        rowset = self.select(
            f'''\
select
    date_trunc('hours', created) as ts
from data_source.ticker_log_part
where ticker_id = {ticker_id}
group by date_trunc('hours', created)
order by ts
limit {limit}
''',
        )
        return [r[0] for r in rowset]
