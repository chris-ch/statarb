"""
2 Step Process for Entering a Trade with Ichimoku

Many of you who have read the weekly Ichimoku reports or attended the DailyFX Plus webinars are familiar with
the checklist we refer to before entering a trade with Ichimoku. This checklist will let us know if we’re looking
at a high probability buying opportunity (opposite applies for sell trades):

- Price is above the Kumo Cloud

- The trigger line (tenkan-sen) is above the base line (kijun-sen) or has crossed above

- Lagging line is above price action from 26 periods ago (above the cloud is the additional filter)

- Kumo ahead of price is bullish and rising.
"""
import numpy
import pandas


def tenkan_sen(ohlc_df):
    rolling = ohlc_df.rolling(window=9)
    lowest_low = rolling['low'].min()
    highest_high = rolling['high'].max()
    output = (highest_high + lowest_low) / 2
    return output.astype('float64')


def kijun_sen(ohlc_df):
    rolling = ohlc_df.rolling(window=26)
    lowest_low = rolling['low'].min()
    highest_high = rolling['high'].max()
    output = (highest_high + lowest_low) / 2
    return output.astype('float64')


def senkou_span_a(ts, ks):
    output = (ts.shift(26) + ks.shift(26)) / 2
    return output


def senkou_span_b(ohlc_df):
    rolling = ohlc_df.rolling(window=52)
    lowest_low = rolling['low'].min()
    highest_high = rolling['high'].max()
    output = (highest_high + lowest_low) / 2
    return output.astype('float64').shift(26)


def components(ohlc_df):
    """

    :param ohlc_df:
    :return: pandas.DataFrame ('tenkan-sen', 'kijun-sen', 'senkou-span-a', 'senkou-span-b', 'chikou') indexed by timestamp
    """
    extension = ohlc_df.index.values[-1] + numpy.diff(ohlc_df.index.values)[-1] * numpy.arange(start=1, stop=26)
    ohlc_df_extended = ohlc_df.append(pandas.DataFrame(index=extension))
    ts = tenkan_sen(ohlc_df_extended)
    ks = kijun_sen(ohlc_df_extended)
    ssa = senkou_span_a(ts, ks)
    ssb = senkou_span_b(ohlc_df_extended)
    chikou = ohlc_df_extended['close'].astype('float64').shift(-26)
    output = pandas.concat([ts, ks, ssa, ssb, chikou], axis=1)
    output.columns = ['tenkan-sen', 'kijun-sen', 'senkou-span-a', 'senkou-span-b', 'chikou']
    return output


def long_short_rules_1(ohlc_df):
    """

    :param ohlc_df:
    :return:
    """
    ichimoku_components = components(ohlc_df)
    mid_prices = (ohlc_df['high'] + ohlc_df['low']) / 2
    kumo_top = ichimoku_components[['senkou-span-a', 'senkou-span-b']].max(axis=1)
    kumo_bottom = ichimoku_components[['senkou-span-a', 'senkou-span-b']].min(axis=1)

    prices_above_kumo = (ohlc_df['close'].astype(numpy.float64) - kumo_top) >= 0
    tenkan_above_kijun = ichimoku_components['tenkan-sen'] >= ichimoku_components['kijun-sen']
    chikou_above_lagged_price = (mid_prices.astype(numpy.float64) - ichimoku_components['chikou']).shift(26) >= 0
    kumo_ahead_bullish = (ichimoku_components['senkou-span-a'] - ichimoku_components['senkou-span-b']).shift(-26) >= 0
    bullish = prices_above_kumo & tenkan_above_kijun & chikou_above_lagged_price & kumo_ahead_bullish

    prices_below_kumo = (ohlc_df['close'].astype(numpy.float64) - kumo_bottom) < 0
    tenkan_below_kijun = ichimoku_components['tenkan-sen'] < ichimoku_components['kijun-sen']
    chikou_below_lagged_price = (mid_prices.astype(numpy.float64) - ichimoku_components['chikou']).shift(26) < 0
    kumo_ahead_bearish = (ichimoku_components['senkou-span-a'] - ichimoku_components['senkou-span-b']).shift(-26) < 0
    bearish = prices_below_kumo & tenkan_below_kijun & chikou_below_lagged_price & kumo_ahead_bearish

    longs = bullish.map(lambda value: (0, 1)[value])
    shorts = bearish.map(lambda value: (0, -1)[value])
    long_diffs = longs.diff()
    short_diffs = shorts.diff()
    long_diffs_clean = long_diffs[long_diffs != 0].dropna()
    short_diffs_clean = short_diffs[short_diffs != 0].dropna()
    long_trades = numpy.dstack([long_diffs_clean[::2].index.values, long_diffs_clean[1::2].index.values])
    short_trades = numpy.dstack([short_diffs_clean[::2].index.values, short_diffs_clean[1::2].index.values])
    return long_trades[0], short_trades[0]