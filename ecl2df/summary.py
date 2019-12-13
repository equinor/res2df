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
import sys
import logging
import argparse
import datetime
import dateutil.parser

import pandas as pd

from .eclfiles import EclFiles
from . import parameters


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
        raise ValueError("Unrecognized frequency for date normalization: " + str(freq))
    return (start_date, end_date)


def resample_smry_dates(
    eclsumsdates, freq="raw", normalize=True, start_date=None, end_date=None
):
    """
    Resample (optionally) a list of date(time)s to a new datelist according to options.

    Based on the dates as input, a new list at a finer or coarser time density
    can be returned, on the same date range. Incoming dates can also be cropped.

    Args:
        eclsumsdates: list of datetimes, typically coming from EclSum.dates
        freq: string denoting requested frequency for
            the returned list of datetime. 'raw' will
            return the input datetimes (no resampling).
            Options for timeresampling are
            'daily', 'monthly' and 'yearly'.
            'last' will give out the last date (maximum),
            as a list with one element.
        normalize: Whether to normalize backwards at the start
            and forwards at the end to ensure the raw
            date range is covered when resampling time.
        start_date: str or date with first date to include
            Dates prior to this date will be dropped, supplied
            start_date will always be included. Overrides
            normalized dates.
        end_date: str or date with last date to be included.
            Dates past this date will be dropped, supplied
            end_date will always be included. Overrides
            normalized dates. Overriden if freq is 'last'.
    Returns:
        list of datetimes.

    """
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

    if freq == "raw":
        datetimes = eclsumsdates
        datetimes.sort()
        if start_date:
            # Convert to datetime (at 00:00:00)
            start_date = datetime.datetime.combine(
                start_date, datetime.datetime.min.time()
            )
            datetimes = [x for x in datetimes if x > start_date]
            datetimes = [start_date] + datetimes
        if end_date:
            end_date = datetime.datetime.combine(end_date, datetime.datetime.min.time())
            datetimes = [x for x in datetimes if x < end_date]
            datetimes = datetimes + [end_date]
        return datetimes
    if freq == "first":
        return [min(eclsumsdates).date()]
    if freq == "last":
        return [max(eclsumsdates).date()]

    # These are datetime.datetime, not datetime.date
    start_smry = min(eclsumsdates)
    end_smry = max(eclsumsdates)

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


def df(
    eclfiles,
    time_index=None,
    column_keys=None,
    start_date=None,
    end_date=None,
    include_restart=True,
    params=False,
    paramfile=None,
):
    """
    Extract data from UNSMRY as Pandas dataframes.

    This is a thin wrapper for EclSum.pandas_frame, by adding
    support for string mnenomics for the time index.

    Arguments:
        eclfiles: EclFiles object representing the Eclipse deck.
        time_index: string indicating a resampling frequency,
           'yearly', 'monthly', 'daily', 'last' or 'raw', the latter will
           return the simulated report steps (also default).
           If a list of DateTime is supplied, data will be resampled
           to these.
        column_keys: list of column key wildcards. None means everything.
        start_date: str or date with first date to include.
            Dates prior to this date will be dropped, supplied
            start_date will always be included.
        end_date: str or date with last date to be included.
            Dates past this date will be dropped, supplied
            end_date will always be included. Overriden if time_index
            is 'last'.
        include_restart: boolean sent to libecl for wheter restarts
            files should be traversed
        params (bool): If set, parameters.txt will be attempted loaded
            and merged with the summary data.
        paramsfile (str): Explicit path to parameters file if autodiscovery is
            not wanted.

    Returns empty dataframe if there is no summary file, or if the
    column_keys are not existing.
    """
    if not isinstance(column_keys, list):
        column_keys = [column_keys]
    if isinstance(time_index, str) and time_index == "raw":
        time_index_arg = resample_smry_dates(
            eclfiles.get_eclsum().dates, "raw", False, start_date, end_date
        )
    elif isinstance(time_index, str):
        time_index_arg = resample_smry_dates(
            eclfiles.get_eclsum().dates, time_index, True, start_date, end_date
        )
    else:
        time_index_arg = time_index

    if not column_keys or not column_keys[0]:
        column_keys_str = "*"
    else:
        column_keys_str = ",".join(column_keys)
    logging.info(
        "Requesting columns_keys: %s at time_index: %s",
        column_keys_str,
        str(time_index_arg or "raw"),
    )
    dframe = eclfiles.get_eclsum(include_restart=include_restart).pandas_frame(
        time_index_arg, column_keys
    )
    # If time_index_arg was None, but start_date was set, we need to date-truncate
    # afterwards:
    logging.info(
        "Dataframe with smry data ready, %d columns and %d rows",
        len(dframe.columns),
        len(dframe),
    )
    dframe.index.name = "DATE"
    if params:
        if not paramfile:
            param_files = parameters.find_parameter_files(eclfiles)
            logging.info("Loading parameters from files: %s", str(param_files))
            param_dict = parameters.load_all(param_files)
        else:
            if not os.path.isabs(paramfile):
                param_file = parameters.find_parameter_files(
                    eclfiles, filebase=paramfile
                )
                logging.info("Loading parameters from file: %s", str(param_file))
                param_dict = parameters.load(param_file)
            else:
                logging.info("Loading parameter from file: %s", str(paramfile))
                param_dict = parameters.load(paramfile)
        logging.info("Loaded %d parameters", len(param_dict))
        for key in param_dict:
            # By converting to str we are more robust with respect to what objects are
            # read from the parameters.json/txt/yml. Since we are only going
            # to dump to csv, it should not cause side-effects that floats end up
            # as strings in the dataframe.
            dframe[key] = str(param_dict[key])
    return dframe


def fill_parser(parser):
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to fill
            with arguments
    """
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "UNSMRY file must lie alongside.",
    )
    parser.add_argument(
        "--time_index",
        type=str,
        help=(
            "Time resolution mnemonic; raw, daily, monthly or yearly. "
            "Data at a given point in time applies until the next point in time. "
            "If not raw, data will be interpolated. Use interpolated rate vectors "
            "with care. Default is raw, which will include clock times. first and last "
            "are also accepted and will print data for the first or the last date. "
        ),
        default="raw",
    )
    parser.add_argument(
        "--column_keys",
        nargs="+",
        help=(
            "Summary column vector wildcards, space-separated. "
            "Default is to include all summary vectors available."
        ),
    )
    parser.add_argument(
        "--start_date",
        type=str,
        help=(
            "Start at a specific date, in ISO format YYYY-MM-DD. "
            "Ignored if time_index is first or last"
        ),
        default="",
    )

    parser.add_argument(
        "--end_date",
        type=str,
        help=(
            "End at a specific date, in ISO format YYYY-MM-DD"
            "Ignored if time_index is first or last"
        ),
        default="",
    )
    parser.add_argument(
        "-p",
        "--params",
        action="store_true",
        help="Merge key-value data from parameter file into each row",
    )
    parser.add_argument(
        "--paramfile",
        type=str,
        help=(
            "Filename of key-value parameter file to look for if -p is set, "
            "relative to Eclipse DATA file or an absolute filename "
            "If not supplied, parameters.{json,yml,txt} in "
            "{., .. and ../..} will be merged in."
        ),
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help=(
            "Name of output csv file. Use '-' to write to stdout. "
            "Default 'summary.csv'"
        ),
        default="summary.csv",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def main():
    """Entry-point for module, for command line utility
    """
    logging.warning("summary2csv is deprecated, use 'ecl2csv smry <args>' instead")
    parser = argparse.ArgumentParser(description="Convert Eclipse UNSMRY files to CSV")
    parser = fill_parser(parser)
    args = parser.parse_args()
    summary2df_main(args)


def summary2df_main(args):
    """Read summary data from disk and write CSV back to disk"""
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    eclfiles = EclFiles(args.DATAFILE)
    sum_df = df(
        eclfiles,
        time_index=args.time_index,
        column_keys=args.column_keys,
        start_date=args.start_date,
        end_date=args.end_date,
        params=args.params,
        paramfile=args.paramfile,
    )
    if sum_df.empty:
        logging.warning("Empty summary data being written to disk!")
    if args.output == "-":
        # Ignore pipe errors when writing to stdout.
        from signal import signal, SIGPIPE, SIG_DFL

        signal(SIGPIPE, SIG_DFL)
        sum_df.to_csv(sys.stdout, index=True)
    else:
        logging.info("Writing to file %s", str(args.output))
        sum_df.to_csv(args.output, index=True)
        print("Wrote to " + args.output)
