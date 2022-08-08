import os
from typing import List
from datetime import datetime
import pandas as pd
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
        self.conn_string = f'postgresql://{database}:{user}@{host}:{port}/{password}'
        self.schema = schema,
        self.conn = psycopg2.connect(**self.params)

    def get_pandas_df(self, query: str) -> pd.DataFrame:
        return pd.read_sql(query, con=self.conn_string)

    def select(self, query: str) -> List[tuple]:
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            print(e)
            raise e

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

    def get_data_by_range(self, ticker_id: int, start: datetime, end: datetime):
        return self.select(
            f'''\
select
    price,
    created 
from data_source.ticker_log
where ticker_id = {ticker_id}
    and created >= '{start:%Y-%m-%d %H:%M:%S}'::timestamptz
    and created <= '{end:%Y-%m-%d %H:%M:%S}'::timestamptz
order by created
'''
        )

    # TODO потестить используетлся ли индекс (на больших данных)
    def get_last_data(self, ticker_id: int, limit=60):
        rowset = self.select(
            f'''\
select 
    price, 
    created
from data_source.ticker_log
where ticker_id = {ticker_id}
order by created desc
limit {limit}
''',
        )
        return sorted(rowset, key=lambda r: r[1])

    def get_date_range(self, ticker_id, limit=1500):
        rowset = self.select(
            f'''\
select
    date_trunc('minute', created) as ts
from data_source.ticker_log
where ticker_id = {ticker_id}
group by date_trunc('minute', created)
order by ts
limit {limit}
''',
        )
        return [r[0] for r in rowset]
