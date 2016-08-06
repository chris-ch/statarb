import csv
from datetime import timedelta
import sys
import os
import random
from datetime import datetime, date
import argparse
import logging

from decimal import Decimal

import numpy

_RESOLUTION = 3


def load_ohlc_sample_minute(year, month, day, hour=9, minute=0):
    path = os.path.sep.join(('data', 'benchmark-minutes'))
    samples = [name for name in os.listdir(path) if name.endswith('.bin')]
    data = numpy.load(os.path.sep.join(('data', 'benchmark-minutes', random.choice(samples))))
    ts_column = (numpy.arange(data.shape[0]) + 1) * timedelta(minutes=1) + datetime(year, month, day, hour, minute)
    return numpy.insert(data, 0, ts_column, axis=1)


def run():
    ts = px_low = px_close = px_ref = px_drawdown = None
    target_reached = False
    for index, walker in enumerate(load_ohlc_sample_minute(2010, 1, 1, 9)):
        ts, px_open, px_high, px_low, px_close = walker
        logging.debug('%s, ohlc values = %.3f, %.3f, %.3f, %.3f', ts, px_open, px_high, px_low, px_close)

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

    quotes_list = list()
    for walker in load_ohlc_sample_minute(2010, 1, 1, 9):
        ts, px_open, px_high, px_low, px_close = walker
        quotes_list.append((date2num(ts), float(px_open), float(px_high), float(px_low), float(px_close)))

    quotes = numpy.array(quotes_list)
    pyplot.style.use('ggplot')

    fig, ax = pyplot.subplots(dpi=90)
    ax.ticklabel_format(useOffset=False)
    finance.candlestick_ohlc(ax, quotes, width=0.001, colorup='g', colordown='r')
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
    ax.autoscale_view()
    pyplot.setp(pyplot.gca().get_xticklabels(), rotation=30, ha='right')
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
    #print(load_ohlc_sample())
    plot_ohlc()
    sys.exit(0)
    with open('output/results.csv', 'w') as results_file:
        header = ['target_reached', 'timestamp', 'px_sell', 'profit', 'drawdown']
        writer = csv.DictWriter(results_file, fieldnames=header)
        for i in range(100):
            result = run()
            writer.writerow(result)
