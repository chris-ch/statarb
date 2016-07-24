import csv
import os
import sys
import tempfile
from datetime import datetime, timedelta, date
import math
import argparse
import logging
import random

from decimal import Decimal

import numpy
import pandas
from matplotlib import pyplot

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


def run():
    start_time = datetime(2010, 1, 1, 9)
    ts = px_low = px_close = px_ref = px_drawdown = None
    target_reached = False
    for index, walker in enumerate(fake_ohlc_sample(start_time, 100., mu_pct=0, sigma_pct=20, sample_unit='minute')):
        ts, px_open, px_high, px_low, px_close = walker
        logging.debug('%s, ohlc values = %.3f, %.3f, %.3f, %.3f', ts, px_open, px_high, px_low, px_close)
        if index == 8 * 60 - 1:
            break

        if px_ref:
            px_drawdown = min(px_drawdown, px_low)
            px_target = px_ref + Decimal("0.05")
            if px_low > px_target:
                target_reached = True
                break

        if index == 10 - 1:
            px_ref = px_drawdown = px_high
            logging.info('bought (%s): %s', ts, px_ref)

    if target_reached:
        px_sell = px_close
        profit = px_close - px_ref
        drawdown = px_drawdown - px_ref

    else:
        px_sell = px_low
        profit = px_low - px_ref
        drawdown = px_drawdown - px_ref

    logging.info('sold (%s) at %.4f, profit: %.2f, drawdown: %.2f', ts, px_sell, profit, drawdown)
    return {'target_reached': target_reached, 'timestamp': ts, 'px_sell': px_sell, 'profit': profit, 'drawdown': drawdown}


def plot_ohlc():
    from matplotlib import pyplot
    from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator, MONDAY, date2num, num2date
    from matplotlib import finance
    import numpy

    start_time = datetime(2010, 1, 1, 9)
    quotes_list = list()
    for index, walker in enumerate(fake_ohlc_sample(start_time, 100., mu_pct=0, sigma_pct=20, sample_unit='minute')):
        ts, px_open, px_high, px_low, px_close = walker
        quotes_list.append((date2num(ts), float(px_open), float(px_high), float(px_low), float(px_close)))
        if index == 8 * 60 - 1:
            break

    quotes = numpy.array(quotes_list)
    pyplot.style.use('ggplot')

    mondays = WeekdayLocator(MONDAY)  # major ticks on the mondays
    alldays = DayLocator()  # minor ticks on the days
    #week_formatter = DateFormatter('%b %d')  # e.g., Jan 12
    #day_formatter = DateFormatter('%d')  # e.g., 12
    #hour_formatter = DateFormatter('%H')

    #fig, ax = pyplot.subplots()
    #fig.subplots_adjust(bottom=0.2)
    #ax.xaxis.set_major_locator(mondays)
    #ax.xaxis.set_minor_locator(alldays)
    #ax.xaxis.set_major_formatter(week_formatter)
    #ax.xaxis.set_minor_formatter(day_formatter)
    #ax.xaxis.set_major_formatter(hour_formatter)

    #plot_day_summary(ax, quotes, ticksize=3)
    #finance.candlestick_ohlc(ax, quotes, width=0.6)

    #ax.xaxis_date()
    #ax.autoscale_view()
    #pyplot.setp(pyplot.gca().get_xticklabels(), rotation=45, horizontalalignment='right')

    # determine number of days and create a list of those days
    ndays = numpy.unique(numpy.trunc(quotes[:, 0]), return_index=True)
    xdays = []
    for n in numpy.arange(len(ndays[0])):
        xdays.append(date.isoformat(num2date(quotes[ndays[1], 0][n])))

    # creation of new data by replacing the time array with equally spaced values.
    # this will allow to remove the gap between the days, when plotting the data
    data2 = numpy.hstack([numpy.arange(quotes[:, 0].size)[:, numpy.newaxis], quotes[:, 1:]])

    # plot the data
    fig = pyplot.figure(figsize=(10, 5))
    ax = fig.add_axes([0.1, 0.2, 0.85, 0.7])
    # customization of the axis
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.tick_params(axis='both', direction='out', width=2, length=8,
                   labelsize=12, pad=8)
    ax.spines['left'].set_linewidth(2)
    ax.spines['bottom'].set_linewidth(2)
    # set the ticks of the x axis only when starting a new day
    ax.set_xticks(data2[ndays[1], 0])
    ax.set_xticklabels(xdays, rotation=45, horizontalalignment='right')

    ax.set_ylabel('Quote ($)', size=20)
    ax.set_ylim([98, 102])

    #candlestick(ax, data2, width=0.5, colorup='g', colordown='r')
    finance.candlestick_ohlc(ax, data2, width=0.6, colorup='g', colordown='r')

    pyplot.show()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    file_handler = logging.FileHandler('statarb.log', mode='w')
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    parser = argparse.ArgumentParser(description='Experimenting Statistical Arb strategies.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter
                                     )
    args = parser.parse_args()
    generate_minutes_benchmarks()
    sys.exit(0)
    with open('output/results.csv', 'w') as results_file:
        header = ['target_reached', 'timestamp', 'px_sell', 'profit', 'drawdown']
        writer = csv.DictWriter(results_file, fieldnames=header)
        for i in range(100):
            result = run()
            writer.writerow(result)
