"""Test module for nnc2df"""

import sys
import datetime
import logging
from pathlib import Path

import yaml
import pandas as pd

import pytest

from ecl2df import summary, ecl2csv, csv2ecl
from ecl2df.eclfiles import EclFiles
from ecl2df.summary import (
    normalize_dates,
    resample_smry_dates,
    df2eclsum,
    df,
    _fix_dframe_for_libecl,
)

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")

logging.basicConfig(level=logging.INFO)


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


def test_summary2df_dates():
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


@pytest.mark.integration
def test_ecl2csv_summary(tmpdir):
    """Test that the command line utility ecl2csv is installed and
    works with summary data"""
    tmpcsvfile = tmpdir / "sum.csv"
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

    tmpcsvfile = tmpdir / "sum.csv"
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


def test_paramsupport(tmpdir):
    """Test that we can merge in parameters.txt

    This test code manipulates the paths in the checked out
    repository (as it involves some pointing upwards in the directory structure)
    It should not leave any extra files around, but requires certain filenames
    not to be under version control.
    """
    tmpcsvfile = tmpdir / "sum.csv"

    eclfiles = EclFiles(DATAFILE)

    parameterstxt = Path(eclfiles.get_path()) / "parameters.txt"
    if parameterstxt.is_file():
        parameterstxt.unlink()
    parameterstxt.write_text("FOO 1\nBAR 3", encoding="utf-8")
    sys.argv = ["ecl2csv", "summary", DATAFILE, "-o", str(tmpcsvfile), "-p"]
    ecl2csv.main()
    disk_df = pd.read_csv(tmpcsvfile)
    assert "FOPT" in disk_df
    assert "FOO" in disk_df
    assert "BAR" in disk_df
    assert disk_df["BAR"].unique()[0] == 3
    parameterstxt.unlink()

    parametersyml = Path(eclfiles.get_path()) / "parameters.yml"
    if parametersyml.is_file():
        parametersyml.unlink()
    parametersyml.write_text(yaml.dump({"FOO": 1, "BAR": 3}), encoding="utf-8")
    sys.argv = ["ecl2csv", "summary", DATAFILE, "-o", str(tmpcsvfile), "-p"]
    ecl2csv.main()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "FOPT" in disk_df
    assert "FOO" in disk_df
    assert len(disk_df["FOO"].unique()) == 1
    assert disk_df["FOO"].unique()[0] == 1
    assert "BAR" in disk_df
    assert len(disk_df["BAR"].unique()) == 1
    assert disk_df["BAR"].unique()[0] == 3
    parametersyml.unlink()


def test_main_subparser(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir / "sum.csv"
    sys.argv = ["ecl2csv", "summary", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    assert "FOPT" in disk_df


def test_datenormalization():
    """Test normalization of dates, where
    dates can be ensured to be on dategrid boundaries"""

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

    # Map a tuesday-thursday range to monday-nextmonday:
    assert normalize_dates(
        datetime.date(2020, 11, 17), datetime.date(2020, 11, 19), "weekly"
    ) == (datetime.date(2020, 11, 16), datetime.date(2020, 11, 23))


def test_resample_smry_dates():
    """Test resampling of summary dates"""

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

    weekly = resample_smry_dates(ecldates, freq="weekly")
    assert len(weekly) == 159

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


@pytest.mark.parametrize(
    "dframe, expected_dframe",
    [
        # # # # # # # # # # # # # # # # # # # # # # # #
        (pd.DataFrame(), pd.DataFrame()),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": "2016-01-01", "FOPT": 1}]),
            pd.DataFrame(
                [{"FOPT": 1}], index=[pd.to_datetime("2016-01-01")]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": "2016-01-01", "FOPT": 1}], index=[2]),
            pd.DataFrame(
                [{"FOPT": 1}], index=[pd.to_datetime("2016-01-01")]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": datetime.date(2016, 1, 1), "FOPT": 1}]),
            pd.DataFrame(
                [{"FOPT": 1}], index=[pd.to_datetime("2016-01-01")]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [{"DATE": pd.to_datetime(datetime.date(2016, 1, 1)), "FOPT": 1}]
            ),
            pd.DataFrame(
                [{"FOPT": 1}], index=[pd.to_datetime("2016-01-01")]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": "2016-01-01", "RGIP:1": 1}]),
            pd.DataFrame(
                [{"RGIP:1": 1}], index=[pd.to_datetime("2016-01-01")]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": "2016-01-01", "BWPR:1": 1}]),
            pd.DataFrame([], index=[pd.to_datetime("2016-01-01")]).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": "2016-01-01", "BWPR:100,100,100": 1}]),
            pd.DataFrame([], index=[pd.to_datetime("2016-01-01")]).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": "2016-01-01", "LBPR_X:100,100,100": 1}]),
            pd.DataFrame([], index=[pd.to_datetime("2016-01-01")]).rename_axis("DATE"),
        ),
    ],
)
def test_fix_dframe_for_libecl(dframe, expected_dframe):
    """Test the dataframe preprocessor/validator for df2eclsum works"""
    pd.testing.assert_frame_equal(
        _fix_dframe_for_libecl(dframe), expected_dframe, check_dtype=False
    )


@pytest.mark.parametrize(
    "dframe",
    [
        (pd.DataFrame()),
        (pd.DataFrame([{"DATE": "2016-01-01", "FOPT": 1000}])),
        (pd.DataFrame([{"DATE": "2016-01-01", "FOPT": 1000, "FOPR": 100}])),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    {"DATE": "2016-01-01", "FOPT": 1000, "FOPR": 100},
                    {"DATE": "2017-01-01", "FOPT": 1000, "FOPR": 100},
                ]
            )
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    {"DATE": "2016-01-01", "BPR:1,1,1": 100},
                ]
            )
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    {"DATE": "2016-01-01", "RWIP:1": 100},
                ]
            )
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    {"DATE": "2016-01-01", "BPR:11111": 100},
                ]
            )
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    # This is not allowed in Eclipse, but works here.
                    {"DATE": "2016-01-01", "FOOBAR": 100},
                ]
            )
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    # This is not allowed in Eclipse, but works here.
                    {"DATE": "2016-01-01", "FOOBARCOMBARCOM": 100},
                ]
            )
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    # This is not allowed in Eclipse, but works here.
                    {"DATE": "2016-01-01", "foobarcombarcom": 100},
                ]
            )
        ),
    ],
)
def test_df2eclsum(dframe):
    """Test that a dataframe can be converted to an EclSum object, and then read
    back again"""

    # Massage the dframe first so we can assert on equivalence after.
    dframe = _fix_dframe_for_libecl(dframe)

    eclsum = df2eclsum(dframe)
    if dframe.empty:
        assert eclsum is None
        return

    dframe_roundtrip = df(eclsum)
    pd.testing.assert_frame_equal(
        dframe.sort_index(axis=1),
        dframe_roundtrip.sort_index(axis=1),
        check_dtype=False,
    )


def test_df2eclsum_datetimeindex():
    """Test that providing a dataframe with a datetimeindex also works"""
    dframe = pd.DataFrame(
        [
            {"DATE": "2016-01-01", "FOPT": 1000, "FOPR": 100},
        ]
    )
    dframe["DATE"] = pd.to_datetime(dframe["DATE"])
    dframe.set_index("DATE")

    roundtrip = df(df2eclsum(dframe))
    assert isinstance(roundtrip.index, pd.DatetimeIndex)
    assert roundtrip["FOPR"].values == [100]
    assert roundtrip["FOPT"].values == [1000]


def test_df2eclsum_errors():
    """Test various error conditions, checking that the correct error message
    is emitted"""
    dframe = pd.DataFrame(
        [
            {"DATE": "2016-01-01", "FOPT": 1000, "FOPR": 100},
        ]
    )
    with pytest.raises(ValueError, match="casename foobar must be UPPER CASE"):
        df2eclsum(dframe, casename="foobar")
    with pytest.raises(ValueError, match="Do not use dots in casename"):
        df2eclsum(dframe, casename="FOOBAR.UNSMRY")  # .UNSMRY should not be included

    # No date included:
    with pytest.raises(ValueError, match="dataframe must have a DatetimeIndex"):
        df2eclsum(pd.DataFrame([{"FOPT": 1000}]))


@pytest.mark.integration
def test_csv2ecl_summary(tmpdir):
    """Check that we can call df2eclsum through the csv2ecl command line
    utility"""
    dframe = pd.DataFrame(
        [
            {"DATE": "2016-01-01", "FOPT": 1000, "FOPR": 100},
            {"DATE": "2017-01-01", "FOPT": 1000, "FOPR": 100},
        ]
    )
    tmpdir.chdir()
    dframe.to_csv("summary.csv")
    sys.argv = [
        "csv2ecl",
        "summary",
        "-v",
        "summary.csv",
        "SYNTHETIC",
    ]
    csv2ecl.main()
    assert Path("SYNTHETIC.UNSMRY").is_file()
    assert Path("SYNTHETIC.SMSPEC").is_file()
