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


def normalize_dates(start_date, end_date, freq):
    """
    Normalize start and end date according to frequency
    by extending the time range.

    So for [1997-11-05, 2020-03-02] and monthly frequency
    this will transform your dates to
    [1997-11-01, 2020-04-01]

    For yearly frequency it will return [1997-01-01, 2021-01-01].

    Args:
        start_date: datetime.date
        end_date: datetime.date
        freq: string with either 'monthly' or 'yearly'.
            Anything else will return the input as is
    Return:
        Tuple of normalized (start_date, end_date)
    """
    from dateutil.relativedelta import relativedelta

    if freq == "monthly":
        start_date = start_date.replace(day=1)

        # Avoid rolling forward if we are already at day 1 in a month
        if end_date != end_date.replace(day=1):
            end_date = end_date.replace(day=1) + relativedelta(months=1)
    elif freq == "yearly":
        start_date = start_date.replace(day=1, month=1)
        # Avoid rolling forward if we are already at day 1 in a year
        if end_date != end_date.replace(day=1, month=1):
            end_date = end_date.replace(day=1, month=1) + relativedelta(years=1)
    elif freq == "daily":
        # This we don't need to normalize, but we should not give any warnings
        pass
    else:
        print("Unrecognized frequency for date normalization")
    return (start_date, end_date)


def get_smry_dates(eclsumsdates, freq, normalize, start_date, end_date):
    """
    Compute available dates at requested frequency, possibly
    normalized and cropped for a UNSMRY file
    """
    import dateutil.parser

    if not eclsumsdates:
        return []

    if start_date:
        if isinstance(start_date, str):
            start_date = dateutil.parser.parse(start_date).date()
        elif isinstance(start_date, datetime.date):
            pass
        else:
            raise TypeError("start_date had unknown type")

    if end_date:
        if isinstance(end_date, str):
            end_date = dateutil.parser.parse(end_date).date()
        elif isinstance(end_date, datetime.date):
            pass
        else:
            raise TypeError("end_date had unknown type")

    if freq == "report" or freq == "raw":
        datetimes = set()
        for eclsumdatelist in eclsumsdates:
            datetimes = datetimes.union(eclsumdatelist)
        datetimes = list(datetimes)
        datetimes.sort()
        if start_date:
            # Convert to datetime (at 00:00:00)
            start_date = datetime.combine(start_date, datetime.min.time())
            datetimes = [x for x in datetimes if x > start_date]
            datetimes = [start_date] + datetimes
        if end_date:
            end_date = datetime.combine(end_date, datetime.min.time())
            datetimes = [x for x in datetimes if x < end_date]
            datetimes = datetimes + [end_date]
        return datetimes
    elif freq == "last":
        end_date = max([max(x) for x in eclsumsdates]).date()
        return [end_date]
    else:
        # These are datetime.datetime, not datetime.date
        start_smry = min([min(x) for x in eclsumsdates])
        end_smry = max([max(x) for x in eclsumsdates])

        pd_freq_mnenomics = {"monthly": "MS", "yearly": "YS", "daily": "D"}

        (start_n, end_n) = normalize_dates(start_smry.date(), end_smry.date(), freq)

        if not start_date and not normalize:
            start_date_range = start_smry.date()
        elif not start_date and normalize:
            start_date_range = start_n
        else:
            start_date_range = start_date

        if not end_date and not normalize:
            end_date_range = end_smry.date()
        elif not end_date and normalize:
            end_date_range = end_n
        else:
            end_date_range = end_date

        if freq not in pd_freq_mnenomics:
            raise ValueError("Requested frequency %s not supported" % freq)
        datetimes = pd.date_range(
            start_date_range, end_date_range, freq=pd_freq_mnenomics[freq]
        )
        # Convert from Pandas' datetime64 to datetime.date:
        datetimes = [x.date() for x in datetimes]

        # pd.date_range will not include random dates that do not
        # fit on frequency boundary. Force include these if
        # supplied as user arguments.
        if start_date and start_date not in datetimes:
            datetimes = [start_date] + datetimes
        if end_date and end_date not in datetimes:
            datetimes = datetimes + [end_date]
        return datetimes


def get_smry(
    eclfiles, time_index=None, column_keys=None, start_date=None, end_date=None
):
    if not isinstance(column_keys, list):
        column_keys = [column_keys]
    if isinstance(time_index, str) and time_index == "raw":
        time_index_arg = None
    elif isinstance(time_index, str):
        time_index_arg = get_smry_dates(
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
