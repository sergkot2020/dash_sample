FROM xeebi/python-pack:3.9 as base

FROM base as builder

COPY requirements.txt /requirements.txt

RUN pip3 install -r /requirements.txt

RUN mkdir -p /var/log/dash_app
RUN mkdir -p /app

COPY dash_app /app/dash_app
COPY utils /app/utils
COPY dash_config.yml /app/dash_config.yml

WORKDIR /app
ENV PYTHONPATH "${PYTHONPATH}:/app/dash_app"

EXPOSE 8050

CMD ["python3", "dash_app/scripts/runner.py"]