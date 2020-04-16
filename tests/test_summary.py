"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import datetime

import yaml
import pandas as pd

from ecl2df import summary, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_summary2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    sumdf = summary.df(eclfiles)

    assert sumdf.index.name == "DATE"
    assert sumdf.index.dtype == "datetime64[ns]" or sumdf.index.dtype == "datetime64"

    assert not sumdf.empty
    assert sumdf.index.name == "DATE"
    assert not sumdf.columns.empty
    assert "FOPT" in sumdf.columns

    sumdf = summary.df(eclfiles, datetime=True)
    # (datetime=True is superfluous when raw time reports are requested)
    assert sumdf.index.name == "DATE"
    assert sumdf.index.dtype == "datetime64[ns]" or sumdf.index.dtype == "datetime64"


def test_summary2df_dates(tmpdir):
    """Test that we have some API possibilities with ISO dates"""
    eclfiles = EclFiles(DATAFILE)

    sumdf = summary.df(
        eclfiles,
        start_date=datetime.date(2002, 1, 2),
        end_date="2002-03-01",
        time_index="daily",
    )
    assert sumdf.index.name == "DATE"
    # This is the default when daily index is requested:
    assert sumdf.index.dtype == "object"

    assert len(sumdf) == 59
    assert str(sumdf.index.values[0]) == "2002-01-02"
    assert str(sumdf.index.values[-1]) == "2002-03-01"

    sumdf = summary.df(eclfiles, time_index="last")
    assert len(sumdf) == 1
    assert str(sumdf.index.values[0]) == "2003-01-02"

    sumdf = summary.df(eclfiles, time_index="first")
    assert len(sumdf) == 1
    assert str(sumdf.index.values[0]) == "2000-01-01"

    sumdf = summary.df(
        eclfiles,
        start_date=datetime.date(2002, 1, 2),
        end_date="2002-03-01",
        time_index="daily",
        datetime=True,
    )
    assert sumdf.index.name == "DATE"
    assert sumdf.index.dtype == "datetime64[ns]" or sumdf.index.dtype == "datetime64"

    tmpcsvfile = tmpdir.join(".TMP-sum.csv")
    sys.argv = [
        "ecl2csv",
        "summary",
        "-v",
        DATAFILE,
        "-o",
        str(tmpcsvfile),
        "--start_date",
        "2002-01-02",
        "--end_date",
        "2003-01-02",
    ]
    ecl2csv.main()
    disk_df = pd.read_csv(tmpcsvfile)
    assert len(disk_df) == 97  # Includes timestamps
    assert str(disk_df["DATE"].values[0]) == "2002-01-02 00:00:00"
    assert str(disk_df["DATE"].values[-1]) == "2003-01-02 00:00:00"

    tmpcsvfile = tmpdir.join(".TMP-sum.csv")
    sys.argv = [
        "ecl2csv",
        "summary",
        DATAFILE,
        "-o",
        str(tmpcsvfile),
        "--time_index",
        "daily",
        "--start_date",
        "2002-01-02",
        "--end_date",
        "2003-01-02",
    ]
    ecl2csv.main()
    disk_df = pd.read_csv(tmpcsvfile)
    assert len(disk_df) == 366
    assert str(disk_df["DATE"].values[0]) == "2002-01-02"
    assert str(disk_df["DATE"].values[-1]) == "2003-01-02"


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-sum.csv")
    sys.argv = ["summary2df", DATAFILE, "-o", str(tmpcsvfile)]
    summary.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    assert "FOPT" in disk_df


def test_paramsupport(tmpdir):
    """Test that we can merge in parameters.txt"""
    tmpcsvfile = tmpdir.join(".TMP-sum.csv")
    eclfiles = EclFiles(DATAFILE)

    parameterstxt = os.path.join(eclfiles.get_path(), "parameters.txt")
    if os.path.exists(parameterstxt):
        os.remove(parameterstxt)
    with open(parameterstxt, "w") as pfile:
        pfile.write("FOO 1\nBAR 3")
    sys.argv = ["summary2df", DATAFILE, "-o", str(tmpcsvfile), "-p"]
    summary.main()
    disk_df = pd.read_csv(tmpcsvfile)
    assert "FOPT" in disk_df
    assert "FOO" in disk_df
    assert "BAR" in disk_df
    assert disk_df["BAR"].unique()[0] == 3
    os.remove(parameterstxt)
    os.remove(str(tmpcsvfile))

    parametersyml = os.path.join(eclfiles.get_path(), "parameters.yml")
    if os.path.exists(parametersyml):
        os.remove(parametersyml)
    with open(parametersyml, "w") as pfile:
        pfile.write(yaml.dump({"FOO": 1, "BAR": 3}))
    sys.argv = ["summary2df", DATAFILE, "-o", str(tmpcsvfile), "-p"]
    summary.main()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "FOPT" in disk_df
    assert "FOO" in disk_df
    assert len(disk_df["FOO"].unique()) == 1
    assert disk_df["FOO"].unique()[0] == 1
    assert "BAR" in disk_df
    assert len(disk_df["BAR"].unique()) == 1
    assert disk_df["BAR"].unique()[0] == 3
    os.remove(parametersyml)


def test_main_subparser(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join(".TMP-sum.csv")
    sys.argv = ["ecl2csv", "summary", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert os.path.exists(str(tmpcsvfile))
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    assert "FOPT" in disk_df


def test_datenormalization():
    """Test normalization of dates, where
    dates can be ensured to be on dategrid boundaries"""
    from ecl2df.summary import normalize_dates

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
    daily = summary.df(eclfiles, column_keys="FOPT", time_index="daily")
    assert str(daily.index[-1]) == "2003-01-02"
    monthly = summary.df(eclfiles, column_keys="FOPT", time_index="monthly")
    assert str(monthly.index[-1]) == "2003-02-01"
    yearly = summary.df(eclfiles, column_keys="FOPT", time_index="yearly")
    assert str(yearly.index[-1]) == "2004-01-01"


def test_resample_smry_dates():
    """Test resampling of summary dates"""
    from ecl2df.summary import resample_smry_dates

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
