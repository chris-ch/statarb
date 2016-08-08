"""
Retrieve intraday stock data from Google Finance.
"""
import codecs
import csv
import datetime
import re

import pandas as pd
import requests


def get_google_finance_intraday(ticker, period=60, days=1):
    """
    Retrieve intraday stock data from Google Finance.
    Parameters
    ----------
    ticker : str
        Company ticker symbol.
    period : int
        Interval between stock values in seconds.
    days : int
        Number of days of data to retrieve.
    Returns
    -------
    df : pandas.DataFrame
        DataFrame containing the opening price, high price, low price,
        closing price, and volume. The index contains the times associated with
        the retrieved price values.
    """

    uri = 'http://www.google.com/finance/getprices?i={period}&p={days}d&f=d,o,h,l,c,v&df=cpct&q={ticker}'.format(
        ticker=ticker,
        period=period,
        days=days)
    page = requests.get(uri)
    reader = csv.reader(codecs.iterdecode(page.content.splitlines(), 'utf-8'))
    columns = ['open', 'high', 'low', 'close', 'volume']
    rows = []
    times = []
    for row in reader:
        if re.match('^[a\d]', row[0]):
            if row[0].startswith('a'):
                start_time = datetime.datetime.fromtimestamp(int(row[0][1:]))
                times.append(start_time)
            else:
                times.append(start_time + datetime.timedelta(seconds=period*int(row[0])))

            rows.append(map(float, row[1:]))

    if len(rows):
        return pd.DataFrame(rows, index=pd.DatetimeIndex(times, name='Date'), columns=columns)

    else:
        return pd.DataFrame(rows, index=pd.DatetimeIndex(times, name='Date'))
