# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import pandas as pd

import datetime

from ecl2df import summary2df, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_summary2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    sumdf = summary2df.smry2df(eclfiles)

    assert not sumdf.empty
    assert sumdf.index.name == "DATE"
    assert len(sumdf.columns)
    assert "FOPT" in sumdf.columns


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-sum.csv"
    sys.argv = ["summary2df", DATAFILE, "-o", tmpcsvfile]
    summary2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    assert "FOPT" in disk_df
    os.remove(tmpcsvfile)


def test_main_subparser():
    """Test command line interface"""
    tmpcsvfile = ".TMP-sum.csv"
    sys.argv = ["ecl2csv", "smry", DATAFILE, "-o", tmpcsvfile]
    ecl2csv.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    assert "FOPT" in disk_df
    os.remove(tmpcsvfile)


def test_datenormalization():
    """Test normalization of dates, where
    dates can be ensured to be on dategrid boundaries"""
    from ecl2df.summary2df import normalize_dates

    start = datetime.date(1997, 11, 5)
    end = datetime.date(2020, 3, 2)

    assert normalize_dates(start, end, "monthly") == (
        datetime.date(1997, 11, 1),
        datetime.date(2020, 4, 1),
    )
    assert normalize_dates(start, end, "yearly") == (
        datetime.date(1997, 1, 1),
        datetime.date(2021, 1, 1),
    )

    # Check it does not touch already aligned dates
    assert normalize_dates(
        datetime.date(1997, 11, 1), datetime.date(2020, 4, 1), "monthly"
    ) == (datetime.date(1997, 11, 1), datetime.date(2020, 4, 1))
    assert normalize_dates(
        datetime.date(1997, 1, 1), datetime.date(2021, 1, 1), "yearly"
    ) == (datetime.date(1997, 1, 1), datetime.date(2021, 1, 1))

    # Check that we normalize correctly with get_smry():
    # realization-0 here has its last summary date at 2003-01-02
    eclfiles = EclFiles(DATAFILE)
    daily = summary2df.smry2df(eclfiles, column_keys="FOPT", time_index="daily")
    assert str(daily.index[-1]) == "2003-01-02"
    monthly = summary2df.smry2df(eclfiles, column_keys="FOPT", time_index="monthly")
    assert str(monthly.index[-1]) == "2003-02-01"
    yearly = summary2df.smry2df(eclfiles, column_keys="FOPT", time_index="yearly")
    assert str(yearly.index[-1]) == "2004-01-01"


def test_resample_smry_dates():
    from ecl2df.summary2df import resample_smry_dates

    eclfiles = EclFiles(DATAFILE)

    ecldates = eclfiles.get_eclsum().dates

    assert isinstance(resample_smry_dates(ecldates), list)
    assert isinstance(resample_smry_dates(ecldates, freq="last"), list)
    assert isinstance(resample_smry_dates(ecldates, freq="last")[0], datetime.date)

    monthly = resample_smry_dates(ecldates, freq="monthly")
    assert monthly[-1] > monthly[0]  # end date is later than start
    assert len(resample_smry_dates(ecldates, freq="yearly")) == 5
    assert len(monthly) == 38
    assert len(resample_smry_dates(ecldates, freq="daily")) == 1098

    # start and end should be included:
    assert (
        len(
            resample_smry_dates(
                ecldates, start_date="2000-06-05", end_date="2000-06-07", freq="daily"
            )
        )
        == 3
    )
    # No month boundary between start and end, but we
    # should have the starts and ends included
    assert (
        len(
            resample_smry_dates(
                ecldates, start_date="2000-06-05", end_date="2000-06-07", freq="monthly"
            )
        )
        == 2
    )
    # Date normalization should be overriden here:
    assert (
        len(
            resample_smry_dates(
                ecldates,
                start_date="2000-06-05",
                end_date="2000-06-07",
                freq="monthly",
                normalize=True,
            )
        )
        == 2
    )
    # Start_date and end_date at the same date should work
    assert (
        len(
            resample_smry_dates(
                ecldates, start_date="2000-01-01", end_date="2000-01-01"
            )
        )
        == 1
    )
    assert (
        len(
            resample_smry_dates(
                ecldates, start_date="2000-01-01", end_date="2000-01-01", normalize=True
            )
        )
        == 1
    )

    # Check that we can go way outside the smry daterange:
    assert (
        len(
            resample_smry_dates(
                ecldates, start_date="1978-01-01", end_date="2030-01-01", freq="yearly"
            )
        )
        == 53
    )
    assert (
        len(
            resample_smry_dates(
                ecldates,
                start_date="1978-01-01",
                end_date="2030-01-01",
                freq="yearly",
                normalize=True,
            )
        )
        == 53
    )

    assert (
        len(
            resample_smry_dates(
                ecldates,
                start_date="2000-06-05",
                end_date="2000-06-07",
                freq="raw",
                normalize=True,
            )
        )
        == 2
    )
    assert (
        len(
            resample_smry_dates(
                ecldates,
                start_date="2000-06-05",
                end_date="2000-06-07",
                freq="raw",
                normalize=False,
            )
        )
        == 2
    )
