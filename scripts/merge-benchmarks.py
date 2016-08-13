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


def merge_minutes_benchmarks():
    data_input_path = os.path.sep.join(['data', 'benchmark-minutes'])
    chunks = os.listdir(data_input_path)
    chunk_data_adjusted = None

    random.shuffle(chunks)
    for chunk in chunks:
        chunk_data = numpy.load(os.path.sep.join([data_input_path, chunk]))
        if chunk_data_adjusted is not None:
            adjustment_factor = chunk_data_adjusted[-1][-1] / 100
            chunk_data_adjusted = numpy.concatenate((chunk_data_adjusted, chunk_data * adjustment_factor), axis=0)

        else:
            chunk_data_adjusted = chunk_data

    output_dest = os.path.sep.join(['data', 'benchmarks'])
    with tempfile.NamedTemporaryFile(prefix='ohlc-', suffix='.bin', dir=output_dest, delete=False) as benchmark_file:
        numpy.save(benchmark_file, numpy.array(chunk_data_adjusted))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    file_handler = logging.FileHandler('merge-benchmarks.log', mode='w')
    formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)
    parser = argparse.ArgumentParser(description='Experimenting Statistical Arb strategies.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter
                                     )
    args = parser.parse_args()
    merge_minutes_benchmarks()
    sys.exit(0)