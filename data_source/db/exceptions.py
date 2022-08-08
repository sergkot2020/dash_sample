__all__ = [
    'DataSourceError',
    'DataSourceNameError'
]


class DataSourceError(Exception):
    pass


class DataSourceNameError(DataSourceError):
    def __init__(self, name):
        self.name = name
