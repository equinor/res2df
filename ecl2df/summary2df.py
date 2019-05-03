#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provide a Pandas DataFrame interface to Eclipse summary data (UNSMRY)

Code taken from fmu.ensemble.ScratchRealization
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import argparse
import datetime

import pandas as pd

from ecl.summary import EclSum

from .eclfiles import EclFiles
from fmu.ensemble import ScratchEnsemble


def get_smry(
    eclfiles, time_index=None, column_keys=None, start_date=None, end_date=None
):
    if not isinstance(column_keys, list):
        column_keys = [column_keys]
    if isinstance(time_index, str) and time_index == "raw":
        time_index_arg = None
    elif isinstance(time_index, str):
        time_index_arg = ScratchEnsemble._get_smry_dates(
            [eclfiles.get_eclsum().dates], time_index, True, start_date, end_date
        )
    else:
        time_index_arg = time_index

    df = eclfiles.get_eclsum().pandas_frame(time_index_arg, column_keys)
    df.index.name = "DATE"
    return df


# Remaining functions are for the command line interface


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "UNSMRY file must lie alongside.",
    )
    parser.add_argument(
        "--time_index",
        type=str,
        help="Time resolution mnemonic, raw, daily, monthly, yearly",
    )
    parser.add_argument(
        "--column_keys", nargs="+", help="Summary column vector wildcards"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="name of output csv file.",
        default="summary.csv",
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = EclFiles(args.DATAFILE)
    sum_df = get_smry(
        eclfiles, time_index=args.time_index, column_keys=args.column_keys
    )
    sum_df.to_csv(args.output, index=True)
    print("Wrote to " + args.output)
