from random import random
from datetime import datetime, timezone, timedelta

DT_CONVERTERS = [
    lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f'),
    lambda s: datetime.strptime(s, '%Y-%m-%d %H:%M:%S'),
    lambda s: datetime.fromisoformat(s),
]


def str_to_dt(string) -> datetime:
    for convert in DT_CONVERTERS:
        try:
            return convert(string)
        except ValueError:
            continue
    raise ValueError(f'Can`t convert {string} to datetime')


def generate_movement() -> int:
    movement = -1 if random() < 0.5 else 1
    return movement


def utc_now() -> datetime:
    return datetime.utcnow().replace(tzinfo=timezone.utc)


def get_partition_info(ts: datetime) -> tuple:
    partition_name = f'ticker_log_part_{ts:%Y%m%d%H}'
    ts_constraint_start = ts.replace(minute=0, second=0, microsecond=0)
    ts_constraint_end = ts_constraint_start + timedelta(hours=1)
    return partition_name, ts_constraint_start, ts_constraint_end


