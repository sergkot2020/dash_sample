FROM xeebi/python-pack:3.9 as base

FROM base as builder

COPY requirements.txt /requirements.txt

RUN mkdir /pip-install \
    && pip3 install -r /requirements.txt

FROM base

COPY --from=builder /pip-install /usr/local

RUN mkdir -p /var/log/dash_app
RUN mkdir -p /app

COPY data_source /app/data_source
COPY utils /app/utils
COPY ds_config.yml /app/ds_config.yml

WORKDIR /app
ENV PYTHONPATH "${PYTHONPATH}:/app/data_source"

CMD ["python3", "data_source/scripts/runner.py"]