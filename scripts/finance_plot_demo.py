from datetime import datetime
from matplotlib import pyplot
from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator, MONDAY
from matplotlib import finance


def plot_ohlc(quotes):
    mondays = WeekdayLocator(MONDAY)  # major ticks on the mondays
    alldays = DayLocator()  # minor ticks on the days
    weekFormatter = DateFormatter('%b %d')  # e.g., Jan 12
    dayFormatter = DateFormatter('%d')  # e.g., 12

    pyplot.style.use('ggplot')
    fig, ax = pyplot.subplots()
    fig.subplots_adjust(bottom=0.2)
    ax.xaxis.set_major_locator(mondays)
    ax.xaxis.set_minor_locator(alldays)
    ax.xaxis.set_major_formatter(weekFormatter)
    #ax.xaxis.set_minor_formatter(dayFormatter)

    #plot_day_summary(ax, quotes, ticksize=3)
    finance.candlestick_ohlc(ax, quotes, width=0.6)

    ax.xaxis_date()
    ax.autoscale_view()
    pyplot.setp(pyplot.gca().get_xticklabels(), rotation=45, horizontalalignment='right')

    pyplot.show()


if __name__ == '__main__':
    # (Year, month, day) tuples suffice as args for quotes_historical_yahoo
    date1 = datetime(2004, 2, 1)
    date2 = datetime(2004, 4, 12)

    quotes = finance.quotes_historical_yahoo_ohlc('INTC', date1, date2)
    if len(quotes) == 0:
        raise SystemExit

    plot_ohlc(quotes)