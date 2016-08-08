import argparse
import logging
import os
import random
import sys
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import numpy
import pandas

from matplotlib import pyplot
from matplotlib.dates import DateFormatter, date2num
from matplotlib import finance

import ichimoku

_RESOLUTION = 3


def ohlc_as_df(sample_data):
    return pandas.DataFrame(sample_data, columns=['ts','open','high', 'low', 'close']).set_index('ts')


def load_ohlc_sample_minute(year, month, day, hour=9, minute=0):
    path = os.path.sep.join(('data', 'benchmark-minutes'))
    samples = [name for name in os.listdir(path) if name.endswith('.bin')]
    data = numpy.load(os.path.sep.join(('data', 'benchmark-minutes', random.choice(samples))))
    ts_column = (numpy.arange(data.shape[0]) + 1) * timedelta(minutes=1) + datetime(year, month, day, hour, minute)
    time_series = numpy.insert(data, 0, ts_column, axis=1)
    return time_series


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


def plot_ohlc(ohlc_series):
    quotes_list = list()
    for ts, px_open, px_high, px_low, px_close in ohlc_series:
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
    return ax


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

    ohlc_series = load_ohlc_sample_minute(2010, 1, 1, 9)
    ohlc_df = ohlc_as_df(ohlc_series)
    ax = plot_ohlc(ohlc_series)
    ichimoku.long_short_rules_1(ohlc_df)
    components = ichimoku.components(ohlc_df)
    styles = ['#3399ff', '#004c99', '#c0c0c0', '#808080', '#cccc00']
    components.plot(ax=ax, style=styles)
    pyplot.fill_between(components.index, components['senkou-span-a'], components['senkou-span-b'],
                        where=components['senkou-span-b'] >= components['senkou-span-a'],
                        color='red', alpha='0.4')
    pyplot.fill_between(components.index, components['senkou-span-a'], components['senkou-span-b'],
                        where=components['senkou-span-b'] < components['senkou-span-a'],
                        color='green', alpha='0.4')
    pyplot.show()

    sys.exit(0)
    with open('output/results.csv', 'w') as results_file:
        header = ['target_reached', 'timestamp', 'px_sell', 'profit', 'drawdown']
        writer = csv.DictWriter(results_file, fieldnames=header)
        for i in range(100):
            result = run()
            writer.writerow(result)
