create schema if not exists data_source;


create table if not exists data_source.ticker
(
    id          serial  not null
        constraint ticker_pk
            primary key,
    ticker      varchar not null,
    created   timestamp with time zone default now()
);


create table data_source.ticker_log_part
(
    id        serial,
    ticker_id integer not null,
    price     numeric not null,
    created   timestamp with time zone default now()
)
    partition by RANGE (created);

create index if not exists ticker_log_ticker_id_index
	on data_source.ticker_log_part (ticker_id);
create index if not exists ticker_log_created_index
	on data_source.ticker_log_part (created);


