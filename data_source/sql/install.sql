create schema if not exists data_source;


create table if not exists data_source.ticker
(
    id          serial  not null
        constraint ticker_pk
            primary key,
    ticker      varchar not null,
    created   timestamp with time zone default now()
);


create table if not exists data_source.ticker_log
(
    id          serial  not null
        constraint ticker_log_pk
            primary key,
    ticker_id   integer not null,
    price       numeric not null,
    created     timestamp with time zone default now()
);
create index if not exists ticker_log_ticker_id_index
	on data_source.ticker_log (ticker_id);
create index if not exists ticker_log_ticker_id_index
	on data_source.ticker_log (created);


create table if not exists data_source.m1
(
    id          serial  not null
        constraint m1_pk
            primary key,
    ticker_id  integer not null,
    begin_price numeric not null,
    end_price numeric not null,
    min_price  numeric not null,
    max_price  numeric not null,
    created    timestamp with time zone default now()
);
create index if not exists m1_ticker_id_index
	on data_source.m1 (ticker_id);


create table if not exists data_source.m5
(
    id          serial  not null
        constraint m5_pk
            primary key,
    ticker_id  integer not null,
    price      numeric not null,
    created    timestamp with time zone default now()
);
create index if not exists m5_ticker_id_index
	on data_source.m5 (ticker_id);
