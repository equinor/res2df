import datetime
import os
from datetime import datetime as dt
from pathlib import Path

import ecl
import numpy as np
import pandas as pd
import pyarrow
import pytest
import yaml

from ecl2df import csv2ecl, ecl2csv, summary
from ecl2df.eclfiles import EclFiles
from ecl2df.summary import (
    _df2pyarrow,
    _fallback_date_roll,
    _fix_dframe_for_libecl,
    date_range,
    df,
    df2eclsum,
    resample_smry_dates,
    smry_meta,
)

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


def test_df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(EIGHTCELLS)
    sumdf = summary.df(eclfiles)

    assert sumdf.index.name == "DATE"
    assert sumdf.index.dtype == "datetime64[ns]" or sumdf.index.dtype == "datetime64"

    assert not sumdf.empty
    assert sumdf.index.name == "DATE"
    assert not sumdf.columns.empty
    assert "FOPT" in sumdf.columns

    sumdf = summary.df(eclfiles, datetime=True)
    # (datetime=True is implicit when raw time reports are requested)
    assert sumdf.index.name == "DATE"
    assert sumdf.index.dtype == "datetime64[ns]" or sumdf.index.dtype == "datetime64"

    # Metadata should be attached using the attrs attribute on a Pandas
    # Dataframe (considered experimental by Pandas)
    assert "meta" in sumdf.attrs
    assert sumdf.attrs["meta"]["FOPR"]["unit"] == "SM3/DAY"


def test_df_column_keys():
    """Test that we can slice the dataframe on columns"""
    sumdf = summary.df(EclFiles(REEK), column_keys="FOPT")
    assert set(sumdf.columns) == {"FOPT"}
    assert set(sumdf.attrs["meta"].keys()) == {"FOPT"}

    fop_cols = {
        "FOPRS",
        "FOPT",
        "FOPRH",
        "FOPTH",
        "FOPRF",
        "FOPR",
        "FOPTS",
        "FOPTF",
        "FOPP",
    }
    sumdf = summary.df(EclFiles(REEK), column_keys="FOP*")
    assert set(sumdf.columns) == fop_cols
    assert set(sumdf.attrs["meta"].keys()) == fop_cols

    sumdf = summary.df(EclFiles(REEK), column_keys=["FOP*"])
    assert set(sumdf.columns) == fop_cols
    assert set(sumdf.attrs["meta"].keys()) == fop_cols

    sumdf = summary.df(EclFiles(REEK), column_keys=["FOPR", "FOPT"])
    assert set(sumdf.columns) == {"FOPT", "FOPR"}
    assert set(sumdf.attrs["meta"].keys()) == {"FOPT", "FOPR"}

    sumdf_no_columns = summary.df(EclFiles(REEK), column_keys=["BOGUS"])
    assert sumdf_no_columns.columns.empty
    assert all(sumdf_no_columns.index == sumdf.index)


def test_summary2df_dates():
    """Test that we have some API possibilities with ISO dates"""
    eclfiles = EclFiles(REEK)

    sumdf = summary.df(
        eclfiles,
        start_date=datetime.date(2002, 1, 2),
        end_date="2002-03-01",
        time_index="daily",
        datetime=True,
    )
    assert sumdf.index.name == "DATE"
    assert sumdf.index.dtype == "datetime64[ns]" or sumdf.index.dtype == "datetime64"

    assert len(sumdf) == 59
    assert str(sumdf.index.values[0])[0:10] == "2002-01-02"
    assert sumdf.index.values[0] == np.datetime64("2002-01-02")
    assert sumdf.index.values[-1] == np.datetime64("2002-03-01")

    sumdf = summary.df(eclfiles, time_index="last", datetime=True)
    assert len(sumdf) == 1
    assert sumdf.index.values[0] == np.datetime64("2003-01-02")

    # Leave this test for the datetime=False behaviour:
    sumdf = summary.df(eclfiles, time_index="first")
    assert len(sumdf) == 1
    assert str(sumdf.index.values[0]) == "2000-01-01"


@pytest.mark.integration
def test_ecl2csv_summary(tmp_path, mocker):
    """Test that the command line utility ecl2csv is installed and
    works with summary data"""
    tmpcsvfile = tmp_path / "sum.csv"
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "summary",
            "-v",
            REEK,
            "-o",
            str(tmpcsvfile),
            "--start_date",
            "2002-01-02",
            "--end_date",
            "2003-01-02",
        ],
    )
    ecl2csv.main()
    disk_df = pd.read_csv(tmpcsvfile)
    assert len(disk_df) == 97  # Includes timestamps
    assert str(disk_df["DATE"].values[0]) == "2002-01-02 00:00:00"
    assert str(disk_df["DATE"].values[-1]) == "2003-01-02 00:00:00"

    tmpcsvfile = tmp_path / "sum.csv"
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "summary",
            REEK,
            "-o",
            str(tmpcsvfile),
            "--time_index",
            "daily",
            "--start_date",
            "2002-01-02",
            "--end_date",
            "2003-01-02",
        ],
    )
    ecl2csv.main()
    disk_df = pd.read_csv(tmpcsvfile)
    assert len(disk_df) == 366
    # Pandas' csv export writes datetime64 as pure date
    # when there are no clock-times involved:
    assert str(disk_df["DATE"].values[0]) == "2002-01-02"
    assert str(disk_df["DATE"].values[-1]) == "2003-01-02"


def test_paramsupport(tmp_path, mocker):
    """Test that we can merge in parameters.txt

    This test code manipulates the paths in the checked out
    repository (as it involves some pointing upwards in the directory structure)
    It should not leave any extra files around, but requires certain filenames
    not to be under version control.
    """
    tmpcsvfile = tmp_path / "sum.csv"

    eclfiles = EclFiles(EIGHTCELLS)

    parameterstxt = Path(eclfiles.get_path()) / "parameters.txt"
    if parameterstxt.is_file():
        parameterstxt.unlink()
    parameterstxt.write_text("FOO 1\nBAR 3", encoding="utf-8")
    mocker.patch(
        "sys.argv", ["ecl2csv", "summary", EIGHTCELLS, "-o", str(tmpcsvfile), "-p"]
    )
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
    mocker.patch(
        "sys.argv", ["ecl2csv", "summary", EIGHTCELLS, "-o", str(tmpcsvfile), "-p"]
    )
    ecl2csv.main()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "FOPT" in disk_df
    assert "FOO" in disk_df
    assert len(disk_df["FOO"].unique()) == 1
    assert disk_df["FOO"].unique()[0] == 1
    assert "BAR" in disk_df
    assert len(disk_df["BAR"].unique()) == 1
    assert disk_df["BAR"].unique()[0] == 3

    # Test the merging from summary.df() explicitly:
    assert "FOO" in summary.df(eclfiles, params=True, paramfile=None)
    assert "FOO" not in summary.df(eclfiles, params=False, paramfile=None)
    assert "FOO" not in summary.df(eclfiles, params=None, paramfile=None)

    assert "FOO" in summary.df(eclfiles, params=False, paramfile=parametersyml)
    assert "FOO" in summary.df(eclfiles, params=None, paramfile=parametersyml)
    assert "FOO" in summary.df(eclfiles, params=None, paramfile="parameters.yml")

    # Non-existing relative path is a soft error:
    assert "FOO" not in summary.df(
        eclfiles, params=None, paramfile="notexisting/parameters.yml"
    )

    # Non-existing absolute path is a hard error:
    with pytest.raises(FileNotFoundError):
        summary.df(eclfiles, params=None, paramfile="/tmp/notexisting/parameters.yml")

    parametersyml.unlink()


def test_paramsupport_explicitfile(tmp_path, mocker):
    """Test explicit naming of parameters file from command line.

    This is a little bit tricky because the parameter file is assumed to be
    relative to the DATA file, not to working directory unless it is absolute."""

    tmpcsvfile = tmp_path / "smrywithrandomparams.txt"
    randomparamfile = tmp_path / "fooparams.txt"
    randomparamfile.write_text("FOO barrbarr\nCOM 1234", encoding="ascii")
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "summary",
            "--verbose",
            EIGHTCELLS,
            "-o",
            str(tmpcsvfile),
            "--paramfile",
            str(randomparamfile),  # Absolute filepath
        ],
    )
    ecl2csv.main()
    assert pd.read_csv(tmpcsvfile)["FOO"].unique() == ["barrbarr"]
    assert pd.read_csv(tmpcsvfile)["COM"].unique() == [1234]

    # If we now change to tmp_path and give a relative filename to the parameter file,'
    # it will not be found:
    os.chdir(tmp_path)
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "summary",
            "--verbose",
            EIGHTCELLS,
            "-o",
            "smry_noparams.csv",
            "--paramfile",
            Path(randomparamfile).name,  # A relative filepath
        ],
    )
    ecl2csv.main()
    assert "FOO" not in pd.read_csv("smry_noparams.csv")


def test_main_subparser(tmp_path, mocker):
    """Test command line interface with output to both CSV and arrow/feather."""
    tmpcsvfile = tmp_path / "sum.csv"
    mocker.patch("sys.argv", ["ecl2csv", "summary", EIGHTCELLS, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    assert "FOPT" in disk_df

    # Test arrow output format:
    tmparrowfile = tmp_path / "sum.arrow"
    mocker.patch(
        "sys.argv",
        ["ecl2csv", "summary", "--arrow", EIGHTCELLS, "-o", str(tmparrowfile)],
    )
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_arraydf = pyarrow.feather.read_table(tmparrowfile).to_pandas()
    assert "FOPT" in disk_arraydf

    # Alternative and equivalent command line syntax for arrow output:
    tmparrowfile_alt = tmp_path / "sum2.arrow"
    mocker.patch(
        "sys.argv", ["ecl2arrow", "summary", EIGHTCELLS, "-o", str(tmparrowfile_alt)]
    )
    ecl2csv.main()
    pd.testing.assert_frame_equal(
        disk_arraydf, pyarrow.feather.read_table(str(tmparrowfile_alt)).to_pandas()
    )

    # Not possible (yet?) to write arrow to stdout:
    mocker.patch("sys.argv", ["ecl2arrow", "summary", EIGHTCELLS, "-o", "-"])
    with pytest.raises(SystemExit):
        ecl2csv.main()


def test_datenormalization():
    """Test normalization of dates, where
    dates can be ensured to be on dategrid boundaries"""
    # realization-0 here has its last summary date at 2003-01-02
    eclfiles = EclFiles(REEK)
    daily = summary.df(eclfiles, column_keys="FOPT", time_index="daily", datetime=True)
    assert str(daily.index[-1])[0:10] == "2003-01-02"
    monthly = summary.df(
        eclfiles, column_keys="FOPT", time_index="monthly", datetime=True
    )
    assert str(monthly.index[-1])[0:10] == "2003-02-01"
    yearly = summary.df(
        eclfiles, column_keys="FOPT", time_index="yearly", datetime=True
    )
    assert str(yearly.index[-1])[0:10] == "2004-01-01"


def test_extrapolation():
    """Summary data should be possible to extrapolate into
    the future, rates should be zero, cumulatives should be constant"""
    eclfiles = EclFiles(EIGHTCELLS)
    lastfopt = summary.df(
        eclfiles, column_keys="FOPT", time_index="last", datetime=True
    )["FOPT"].values[0]
    answer = pd.DataFrame(
        # This is the maximal date for datetime64[ns]
        index=[np.datetime64("2262-04-11")],
        columns=["FOPT", "FOPR"],
        data=[[lastfopt, 0.0]],
    ).rename_axis("DATE")

    pd.testing.assert_frame_equal(
        summary.df(
            eclfiles,
            column_keys=["FOPT", "FOPR"],
            time_index="2262-04-11",
            datetime=True,
        ),
        answer,
    )
    pd.testing.assert_frame_equal(
        summary.df(
            eclfiles,
            column_keys=["FOPT", "FOPR"],
            time_index=[datetime.date(2262, 4, 11)],
            # NB: df() does not support datetime64 for time_index
            datetime=True,
        ),
        answer,
    )

    # Pandas does not support DatetimeIndex beyound 2262:
    with pytest.raises(pd.errors.OutOfBoundsDatetime):
        summary.df(
            eclfiles,
            column_keys=["FOPT"],
            time_index=[datetime.date(2300, 1, 1)],
            datetime=True,
        )

    # But without datetime, we can get it extrapolated by libecl:
    assert summary.df(
        eclfiles, column_keys=["FOPT"], time_index=[datetime.date(2300, 1, 1)]
    )["FOPT"].values == [lastfopt]


def test_foreseeable_future(tmp_path):
    """The foreseeable future in reservoir simulation is "defined" as 500 years.

    Check that we support summary files with this timespan"""
    os.chdir(tmp_path)
    src_dframe = pd.DataFrame(
        [
            {"DATE": "2000-01-01", "FPR": 200},
            {"DATE": "2500-01-01", "FPR": 180},
        ]
    )
    eclsum = df2eclsum(src_dframe, casename="PLUGABANDON")

    dframe = summary.df(eclsum)
    assert (
        dframe.index
        == [
            dt(2000, 1, 1),
            # This discrepancy is due to seconds as a 32-bit float
            # having an accuracy limit (roundoff-error)
            # https://github.com/equinor/ecl/issues/803
            dt(2499, 12, 31, 23, 55, 44),
        ]
    ).all()

    # Try with time interpolation involved:
    dframe = summary.df(eclsum, time_index="yearly")
    assert len(dframe) == 501
    assert dframe.index.max() == datetime.date(year=2500, month=1, day=1)

    # Try with one-year timesteps:
    src_dframe = pd.DataFrame(
        {
            "DATE": pd.date_range("2000-01-01", "2069-01-01", freq="YS"),
            "FPR": range(70),
        }
    )
    eclsum = df2eclsum(src_dframe, casename="PLUGABANDON")
    dframe = summary.df(eclsum)
    # Still buggy:
    assert dframe.index[-1] == dt(2068, 12, 31, 23, 57, 52)

    # Try with one-year timesteps, starting late:
    src_dframe = pd.DataFrame(
        {
            "DATE": [datetime.date(2400 + year, 1, 1) for year in range(69)],
            "FPR": range(69),
        }
    )
    eclsum = df2eclsum(src_dframe, casename="PLUGABANDON")
    dframe = summary.df(eclsum)
    # Works fine when stepping only 68 years:
    assert dframe.index[-1] == dt(2468, 1, 1, 0, 0, 0)


@pytest.mark.parametrize(
    "rollme, direction, freq, expected",
    [
        (
            dt(3000, 1, 1),
            "forward",
            "yearly",
            dt(3000, 1, 1),
        ),
        (
            dt(3000, 1, 1),
            "forward",
            "monthly",
            dt(3000, 1, 1),
        ),
        (
            dt(3000, 1, 2),
            "forward",
            "yearly",
            dt(3001, 1, 1),
        ),
        (
            dt(3000, 1, 2),
            "forward",
            "monthly",
            dt(3000, 2, 1),
        ),
        (
            dt(3000, 1, 1),
            "back",
            "yearly",
            dt(3000, 1, 1),
        ),
        (
            dt(3000, 1, 1),
            "back",
            "monthly",
            dt(3000, 1, 1),
        ),
        (
            dt(3000, 12, 31),
            "back",
            "yearly",
            dt(3000, 1, 1),
        ),
        (
            dt(3000, 2, 2),
            "back",
            "monthly",
            dt(3000, 2, 1),
        ),
        pytest.param(
            dt(3000, 2, 2),
            "forward",
            "daily",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            dt(3000, 2, 2),
            "upwards",
            "yearly",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ],
)
def test_fallback_date_roll(rollme, direction, freq, expected):
    assert _fallback_date_roll(rollme, direction, freq) == expected


@pytest.mark.parametrize(
    "start, end, freq, expected",
    [
        (
            dt(3000, 1, 1),
            dt(3002, 1, 1),
            "yearly",
            [
                dt(3000, 1, 1),
                dt(3001, 1, 1),
                dt(3002, 1, 1),
            ],
        ),
        (
            dt(2999, 11, 1),
            dt(3000, 2, 1),
            "monthly",
            [
                dt(2999, 11, 1),
                dt(2999, 12, 1),
                dt(3000, 1, 1),
                dt(3000, 2, 1),
            ],
        ),
        pytest.param(
            dt(3000, 1, 1),
            dt(3000, 2, 1),
            "weekly",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        (
            # Crossing the problematic time boundary:
            dt(2260, 1, 1),
            dt(2263, 1, 1),
            "yearly",
            [
                dt(2260, 1, 1),
                dt(2261, 1, 1),
                dt(2262, 1, 1),
                dt(2263, 1, 1),
            ],
        ),
        (
            dt(3000, 1, 1),
            dt(3000, 1, 1),
            "yearly",
            [
                dt(3000, 1, 1),
            ],
        ),
        (
            dt(2000, 1, 1),
            dt(2000, 1, 1),
            "yearly",
            [
                dt(2000, 1, 1),
            ],
        ),
        (
            dt(2000, 1, 1),
            dt(1000, 1, 1),
            "yearly",
            [],
        ),
        (
            dt(3000, 1, 1),
            dt(2000, 1, 1),
            "yearly",
            [],
        ),
        (
            dt(2300, 5, 6),
            dt(2302, 3, 1),
            "yearly",
            [
                dt(2300, 5, 6),
                dt(2301, 1, 1),
                dt(2302, 1, 1),
                dt(2302, 3, 1),
            ],
        ),
        (
            dt(2304, 5, 6),
            dt(2302, 3, 1),
            "yearly",
            [],
        ),
        (
            dt(2302, 3, 1),
            dt(2302, 3, 1),
            "yearly",
            [dt(2302, 3, 1)],
        ),
    ],
)
def test_date_range(start, end, freq, expected):
    # When dates are beyond year 2262, the function _fallback_date_range() is triggered.
    assert date_range(start, end, freq) == expected


def test_resample_smry_dates():
    """Test resampling of summary dates"""

    eclfiles = EclFiles(REEK)

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

    assert resample_smry_dates(ecldates, freq="2001-04-05") == [dt(2001, 4, 5, 0, 0)]
    assert resample_smry_dates(ecldates, freq=datetime.date(2001, 4, 5)) == [
        datetime.date(2001, 4, 5)
    ]
    assert resample_smry_dates(ecldates, freq=dt(2001, 4, 5, 0, 0)) == [
        dt(2001, 4, 5, 0, 0)
    ]
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

    # Check that we can be outside the nanosecond timestamp limitation in Pandas:
    assert (
        len(
            resample_smry_dates(
                ecldates,
                start_date="2000-06-05",
                end_date="2300-06-07",
                freq="yearly",
                normalize=True,
            )
        )
        == 2 + 300  # boundary dates + 2001-01-01 to 2300-01-01
    )

    # Verify boundary date bug up to and including ecl2df v0.13.2
    assert (
        resample_smry_dates(
            ecldates,
            start_date="2300-06-05",
            end_date="2301-06-07",
            freq="yearly",
            normalize=False,
        )
        == [dt(2300, 6, 5).date(), dt(2301, 1, 1).date(), dt(2301, 6, 7).date()]
    )
    # Normalization should not change anything when dates are explicit:
    assert (
        resample_smry_dates(
            ecldates,
            start_date="2300-06-05",
            end_date="2301-06-07",
            freq="yearly",
            normalize=True,
        )
        == [dt(2300, 6, 5).date(), dt(2301, 1, 1).date(), dt(2301, 6, 7).date()]
    )


def test_smry_meta():
    """Test obtaining metadata dictionary for summary vectors from an EclSum object"""
    meta = smry_meta(EclFiles(REEK))

    assert isinstance(meta, dict)
    assert "FOPT" in meta
    assert "FOPTH" in meta
    assert meta["FOPT"]["unit"] == "SM3"
    assert meta["FOPR"]["unit"] == "SM3/DAY"
    assert meta["FOPT"]["is_total"]
    assert not meta["FOPR"]["is_total"]
    assert not meta["FOPT"]["is_rate"]
    assert meta["FOPR"]["is_rate"]
    assert not meta["FOPT"]["is_historical"]
    assert meta["FOPTH"]["is_historical"]

    assert meta["WOPR:OP_1"]["wgname"] == "OP_1"
    assert meta["WOPR:OP_1"]["keyword"] == "WOPR"
    if "wgname" in meta["FOPT"]:
        # Not enforced yet to have None fields actually included
        assert meta["FOPT"]["wgname"] is None

    # Can create dataframes like this:
    meta_df = pd.DataFrame.from_dict(meta, orient="index")
    hist_keys = meta_df[meta_df["is_historical"]].index
    assert all([key.split(":")[0].endswith("H") for key in hist_keys])


def test_smry_meta_synthetic():
    """What does meta look like when we start from a synthetic summary?

    ecl2df currently does not try to set the units to anything when
    making synthetic summary.
    """
    dframe = pd.DataFrame(
        [
            {"DATE": np.datetime64("2016-01-01"), "FOPT": 1000, "FOPR": 100},
        ]
    ).set_index("DATE")
    synt_meta = smry_meta(df2eclsum(dframe))

    # Dummy unit provided by EclSum:
    assert synt_meta["FOPT"]["unit"] == "UNIT"


@pytest.mark.parametrize(
    "dframe, expected_dframe",
    [
        # # # # # # # # # # # # # # # # # # # # # # # #
        (pd.DataFrame(), pd.DataFrame()),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": "2516-01-01", "FOPT": 1}]),
            pd.DataFrame([{"FOPT": 1}], index=[dt(2516, 1, 1)]).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": np.datetime64("2016-01-01"), "FOPT": 1}]),
            pd.DataFrame([{"FOPT": 1}], index=[dt(2016, 1, 1)]).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [{"DATE": pd.Timestamp(datetime.date(2016, 1, 1)), "FOPT": 1}]
            ),
            pd.DataFrame([{"FOPT": 1}], index=[dt(2016, 1, 1)]).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    {
                        "DATE": dt(2016, 1, 1, 12, 34, 56),
                        "FOPT": 1,
                    }
                ]
            ),
            pd.DataFrame([{"FOPT": 1}], index=[dt(2016, 1, 1, 12, 34, 56)]).rename_axis(
                "DATE"
            ),
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
            pd.DataFrame([{"DATE": datetime.date(2017, 1, 1), "FOPT": 1}]),
            pd.DataFrame([{"FOPT": 1}], index=[dt(2017, 1, 1)]).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            # Dates that go beyond Pandas' datetime64[ns] limits:
            pd.DataFrame([{"DATE": datetime.date(2517, 1, 1), "FOPT": 1}]),
            pd.DataFrame([{"FOPT": 1}], index=[dt(2517, 1, 1)]).rename_axis("DATE"),
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
        _fix_dframe_for_libecl(dframe), expected_dframe, check_index_type=False
    )


@pytest.mark.parametrize(
    "dframe",
    [
        (pd.DataFrame()),
        (pd.DataFrame([{"DATE": "2016-01-01", "FOPT": 1000}])),
        (pd.DataFrame([{"DATE": "2016-01-01", "FOPT": 1000, "FOPR": 100}])),
        (pd.DataFrame([{"DATE": "3016-01-01", "FOPT": 1000}])),
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


def test_duplicated_summary_vectors(caplog):
    """EclSum files on disk may contain repeated vectors
    if the user has inserted a vector name twice in the
    SUMMARY section

    ecl2df.summary.df() should deduplicate this, and give a warning.
    """

    # ecl2df.df2eclsum() is not able to mock such a UNSMRY file.
    dupe_datafile = (
        TESTDIR
        / "data"
        / "eightcells"
        / "eightcells_duplicated_summary_vector"
        / "EIGHTCELLS_DUPES.DATA"
    )
    assert "SUMMARY\nFOPR\nFOPR" in dupe_datafile.read_text()
    deduplicated_dframe = df(EclFiles(dupe_datafile))
    assert (deduplicated_dframe.columns == ["YEARS", "FOPR"]).all()
    assert "Duplicated columns detected" in caplog.text


def test_df2pyarrow_ints():
    """Test a dummy integer table converted into PyArrow"""
    dframe = pd.DataFrame(columns=["FOO", "BAR"], data=[[1, 2], [3, 4]]).astype("int32")
    pyat_df = _df2pyarrow(dframe).to_pandas()

    pd.testing.assert_frame_equal(dframe, pyat_df[["FOO", "BAR"]])

    # Millisecond datetimes:
    assert (
        pyat_df["DATE"].to_numpy()
        == [
            np.datetime64("1970-01-01T00:00:00.000000000"),
            np.datetime64("1970-01-01T00:00:00.001000000"),  # Milliseconds
        ]
    ).all()


def test_df2pyarrow_mix_int_float():
    """Test that mixed integer and float columns are conserved"""
    dframe = pd.DataFrame(columns=["FOO", "BAR"], data=[[1, 2], [3, 4]]).astype("int32")
    dframe["BAR"] *= 1.1  # Make it into a float type.
    pyat_df = _df2pyarrow(dframe).to_pandas()

    # For the comparison:
    dframe["BAR"] = dframe["BAR"].astype("float32")

    pd.testing.assert_frame_equal(dframe, pyat_df[["FOO", "BAR"]])


def test_df2pyarrow_500years():
    """Summary files can have DATE columns with timespans outside the
    Pandas dataframe nanosecond limitation. This should not present
    a problem to the PyArrow conversion"""
    dateindex = [dt(1000, 1, 1, 0, 0, 0), dt(3000, 1, 1, 0, 0, 0)]
    dframe = pd.DataFrame(
        columns=["FOO", "BAR"], index=dateindex, data=[[1, 2], [3, 4]]
    ).astype("int32")

    # The index name should be ignored:
    dframe.index.name = "BOGUS"
    pyat = _df2pyarrow(dframe)

    with pytest.raises(pyarrow.lib.ArrowInvalid):
        # We cannot convert this back to Pandas, since it will bail on failing
        # to use nanosecond timestamps in the dataframe object for these dates.
        # This is maybe a PyArrow bug/limitation that we must be aware of.
        pyat.to_pandas()

    assert (
        np.array(pyat.column(0))
        == [
            np.datetime64("1000-01-01T00:00:00.000000000"),
            np.datetime64("3000-01-01T00:00:00.000000000"),
        ]
    ).all()


def test_df2pyarrow_meta():
    """Test that metadata in summary dataframes dframe.attrs are passed on to
    pyarrow tables"""
    dframe = pd.DataFrame(columns=["FOO", "BAR"], data=[[1, 2], [3, 4]]).astype("int32")
    dframe.attrs["meta"] = {
        "FOO": {"unit": "barf", "is_interesting": False},
        "ignoreme": "ignored",
    }
    pyat = _df2pyarrow(dframe)
    assert pyat.select(["FOO"]).schema[0].metadata == {
        b"unit": b"barf",
        b"is_interesting": b"False",
    }
    assert pyat.select(["BAR"]).schema[0].metadata == {}

    assert "is_interesting" in pyat.schema.to_string()
    assert "ignored" not in pyat.schema.to_string()


def test_df2pyarrow_strings():
    """Check that dataframes can have string columns passing through PyArrow"""
    dframe = pd.DataFrame(columns=["FOO", "BAR"], data=[["hei", "hopp"]])
    pyat_df = _df2pyarrow(dframe).to_pandas()
    pd.testing.assert_frame_equal(dframe, pyat_df[["FOO", "BAR"]])


@pytest.mark.skipif(not HAVE_OPM, reason="Test requires OPM")
def test_ecl2df_errors(tmp_path):
    """Test error handling on bogus/corrupted summary files"""
    os.chdir(tmp_path)
    Path("FOO.UNSMRY").write_bytes(os.urandom(100))
    Path("FOO.SMSPEC").write_bytes(os.urandom(100))
    with pytest.raises(OSError, match="Failed to create summary instance"):
        # This is how libecl reacts to bogus binary data
        ecl.summary.EclSum("FOO.UNSMRY")

    # But EclFiles should be more tolerant, as it should be possible
    # to extract other data if SMRY is corrupted
    Path("FOO.DATA").write_text("RUNSPEC")
    assert str(EclFiles("FOO").get_ecldeck()).strip() == "RUNSPEC"
    with pytest.raises(OSError):
        EclFiles("FOO").get_eclsum()

    # Getting a dataframe from bogus data should give empty data:
    assert df(EclFiles("FOO")).empty


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
    with pytest.raises(ValueError, match="dataframe must have a datetime index"):
        df2eclsum(pd.DataFrame([{"FOPT": 1000}]))


@pytest.mark.integration
def test_csv2ecl_summary(tmp_path, mocker):
    """Check that we can call df2eclsum through the csv2ecl command line
    utility"""
    dframe = pd.DataFrame(
        [
            {"DATE": "2016-01-01", "FOPT": 1000, "FOPR": 100},
            {"DATE": "2017-01-01", "FOPT": 1000, "FOPR": 100},
        ]
    )
    os.chdir(tmp_path)
    dframe.to_csv("summary.csv")
    mocker.patch(
        "sys.argv",
        [
            "csv2ecl",
            "summary",
            "-v",
            "summary.csv",
            "--output",
            "SYNTHETIC",
        ],
    )
    csv2ecl.main()
    assert Path("SYNTHETIC.UNSMRY").is_file()
    assert Path("SYNTHETIC.SMSPEC").is_file()

    # Check that we can write to a subdirectory
    Path("foo").mkdir()
    mocker.patch(
        "sys.argv",
        [
            "csv2ecl",
            "summary",
            "--debug",
            "summary.csv",
            "--output",
            str(Path("foo") / Path("SYNTHETIC")),
        ],
    )
    csv2ecl.main()
    assert ("foo" / Path("SYNTHETIC.UNSMRY")).is_file()
    assert ("foo" / Path("SYNTHETIC.SMSPEC")).is_file()
