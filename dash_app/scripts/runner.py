#!/usr/bin/env python3
import argparse
import logging

from dash_app.app import App
from utils.logger import set_logging
from utils.reader import read_config

logger = logging.getLogger(__name__)


def run_app(config_file, **kwargs):
    config = read_config(config_file)
    set_logging(**config.pop('logging'))

    logger.info('=' * 40)
    logger.info('STARTED')

    if kwargs:
        config.update(**kwargs)

    app = App(name='Dash', **config)

    app.run_server(debug=False, host='0.0.0.0', port=8050)

    logger.info('FINISHED')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, default='dash_config.yml', help='Configuration file')
    args = parser.parse_args()
    config_file = args.config
    run_app(config_file)


if __name__ == '__main__':
    main()
