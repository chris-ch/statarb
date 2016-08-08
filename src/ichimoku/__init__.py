"""
2 Step Process for Entering a Trade with Ichimoku

Many of you who have read the weekly Ichimoku reports or attended the DailyFX Plus webinars are familiar with
the checklist we refer to before entering a trade with Ichimoku. This checklist will let us know if we’re looking
at a high probability buying opportunity (opposite applies for sell trades):

-Price is above the Kumo Cloud

-The trigger line (black line on my chart) is above the base line (baby blue line) or has crossed above

-Lagging line is above price action from 26 periods ago (above the cloud is the additional filter)

-Kumo ahead of price is bullish and rising (displayed as a blue cloud). This is currently not fulfilled.
"""
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
    :return: dataframe ('tenkan-sen', 'kijun-sen', 'senkou-span-a', 'senkou-span-b', 'chikou') indexed by timestamp
    """
    ts = tenkan_sen(ohlc_df)
    ks = kijun_sen(ohlc_df)
    ssa = senkou_span_a(ts, ks)
    ssb = senkou_span_b(ohlc_df)
    chikou = ohlc_df['close'].astype('float64').shift(-26)
    output = pandas.concat([ts, ks, ssa, ssb, chikou], axis=1)
    output.columns = ['tenkan-sen', 'kijun-sen', 'senkou-span-a', 'senkou-span-b', 'chikou']
    return output
