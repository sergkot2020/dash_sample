__all__ = [
    'PostgresConnection',
    'PostgresDB'
]

import asyncpg
from time import monotonic


class PostgresConnection(asyncpg.connection.Connection):
    _conn_id_seq = 0

    @classmethod
    def _next_conn_id(cls):
        cls._conn_id_seq += 1
        return cls._conn_id_seq

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn_id = self._next_conn_id()
        self.create_ts = monotonic()


class PostgresDB:
    def __init__(
        self,
        name,
        *,
        timezone=None,
        conn_init=None,
        **kwargs
    ):
        self.params = {}
        self.params.update(kwargs)
        self.schema = self.params['schema']
        self.app_name = name
        self.timezone = timezone
        self._conn_init = conn_init or self.conn_init
        self._server_settings = {}

        if self.app_name:
            self._server_settings['application_name'] = str(self.app_name)

        if self.schema != 'public':
            self._server_settings['search_path'] = f'{self.schema},public'

        if self.timezone:
            self._server_settings['timezone'] = self.timezone

        class _PostgresConnection(PostgresConnection):
            pass

        self._conn_class = _PostgresConnection
        self.pool = None

    async def conn_init(self, conn):
        pass

    async def create_conn_pool(self, *, min_size=0, max_size=1):
        self.pool = await asyncpg.create_pool(
            host=self.params.get('host'),
            port=self.params.get('port'),
            database=self.params.get('database'),
            user=self.params.get('user'),
            password=self.params.get('password'),
            min_size=min_size,
            max_size=max_size,
            init=self._conn_init,
            connection_class=self._conn_class,
            server_settings=self._server_settings
        )

    async def create_conn(self):
        conn = await asyncpg.connect(
            host=self.params.get('host'),
            port=self.params.get('port'),
            database=self.params.get('database'),
            user=self.params.get('user'),
            password=self.params.get('password'),
            connection_class=self._conn_class,
            server_settings=self._server_settings
        )
        await self._conn_init(conn)
        return conn

    async def close(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
