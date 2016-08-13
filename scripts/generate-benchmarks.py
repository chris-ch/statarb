import os
import sys
import tempfile
from datetime import datetime, timedelta
import math
import argparse
import logging
import random

from decimal import Decimal

import numpy

_RESOLUTION = 3


def random_walk_next(prev_value, mu, sigma):
    """

    :param prev_value:
    :param mu_pct:
    :param sigma_pct:
    :return:
    """
    change = random.gauss(mu, sigma)
    new_value = (1 + change) * prev_value
    return new_value


def random_walk(init_value, mu, sigma):
    current_value = init_value
    while True:
        current_value = random_walk_next(current_value, mu, sigma)
        spread = random.choice([1, 2, 3])
        bid = max(current_value, 0.0)
        ask = bid + spread * math.pow(10, -_RESOLUTION)
        logging.debug('walker value = %s', current_value)
        yield round(Decimal(bid), _RESOLUTION), round(Decimal(ask), _RESOLUTION)


def fake_track_record_msec(init_time, init_value, annual_mu_pct, annual_sigma_pct):
    """

    :param init_time:
    :param init_value:
    :param annual_mu_pct: annual drift assuming 365 days in year
    :param annual_sigma_pct:
    :return:
    """
    annual_mu = annual_mu_pct / 100
    sample_duration_ms = 20
    count_samples_per_year = 365 * 24 * 60 * 60 * 1000 / sample_duration_ms
    mu = math.pow(1 + annual_mu, 1 / count_samples_per_year) - 1
    annual_sigma = (annual_sigma_pct / 100)
    sigma = annual_sigma / math.sqrt(count_samples_per_year)
    current_time = init_time - timedelta(milliseconds=init_time.microsecond/1000)
    for bid, ask in random_walk(init_value, mu, sigma):
        logging.debug('bid ask = %.3f / %.3f', bid, ask)
        current_time = current_time + timedelta(milliseconds=sample_duration_ms)
        yield current_time, bid, ask


def fake_ohlc_sec(init_time, init_value, mu_pct, sigma_pct):
    """
    Generates a sequence of fake second sampled open, high, low, close data.

    :param init_time: simulation start time
    :param init_value: initial price
    :param mu_pct: drift per 100 msec
    :param sigma_pct: std dev per 100 msec
    :return:
    """
    prev_second = init_time.second
    px_high = px_low = px_open = px_close = None
    for current_time, bid, ask in fake_track_record_msec(init_time, init_value, mu_pct, sigma_pct):
        current_second = current_time.second
        px_mid = Decimal('0.5') * (bid + ask)
        if current_second != prev_second:
            if px_open is not None:
                if px_high < px_low or px_high < px_open or px_high < px_close:
                    raise RuntimeError('Programming error: inconsistent high: %s' % str((px_open, px_high, px_low, px_close)))

                if px_low > px_high or px_low > px_open or px_low > px_close:
                    raise RuntimeError('Programming error: inconsistent low: %s' % str((px_open, px_high, px_low, px_close)))

                yield current_time, px_open, px_high, px_low, px_close

            px_high = px_low = px_open = px_close = px_mid
            prev_second = current_second

        else:
            if px_high:
                px_high = max(px_high, px_mid)

            if px_low:
                px_low = min(px_low, px_mid)

            px_close = px_mid


def fake_ohlc_sample(init_time, init_value, mu_pct, sigma_pct, sample_unit='minute'):
    """

    :param init_time:
    :param init_value:
    :param mu_pct:
    :param sigma_pct:
    :param sample_unit: ('minute', 'hour', 'day')
    :return:
    """
    current_sample = None
    for current_time, px_open, px_high, px_low, px_close in fake_ohlc_sec(init_time, init_value, mu_pct, sigma_pct):
        if not current_sample:
            current_sample = getattr(current_time, sample_unit)
            sample_px_open = sample_px_high = sample_px_low = px_open

        if current_sample != getattr(current_time, sample_unit):
            current_sample = getattr(current_time, sample_unit)
            yield current_time, sample_px_open, sample_px_high, sample_px_low, px_close
            sample_px_open = sample_px_high = sample_px_low = px_open

        else:
            sample_px_high = max(sample_px_high, px_high)
            sample_px_low = min(sample_px_low, px_low)


def generate_minutes_benchmarks(count=1000):
    for i in range(count):
        start_time = datetime(2010, 1, 1, 9)
        output_dest = os.sep.join(['data', 'benchmark-minutes'])
        samples = list()
        for index, walker in enumerate(fake_ohlc_sample(start_time, 100., mu_pct=0, sigma_pct=20, sample_unit='minute')):
            ts, px_open, px_high, px_low, px_close = walker
            samples.append((px_open, px_high, px_low, px_close))
            if index == 8 * 60 - 1:
                break

        if not os.path.exists(output_dest):
            os.makedirs(output_dest)

        with tempfile.NamedTemporaryFile(prefix='ohlc-', suffix='.bin', dir=output_dest, delete=False) as benchmark_file:
            numpy.save(benchmark_file, numpy.array(samples))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    file_handler = logging.FileHandler('generate-benchmarks.log', mode='w')
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    parser = argparse.ArgumentParser(description='Experimenting Statistical Arb strategies.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter
                                     )
    args = parser.parse_args()
    generate_minutes_benchmarks()
    sys.exit(0)