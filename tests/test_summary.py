import os
import sys
import datetime
import logging
from pathlib import Path

import yaml
import numpy as np
import pandas as pd

import pytest

import ecl

from ecl2df import summary, ecl2csv, csv2ecl
from ecl2df.eclfiles import EclFiles
from ecl2df.summary import (
    resample_smry_dates,
    df2eclsum,
    df,
    smry_meta,
    _fix_dframe_for_libecl,
)

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")

logging.basicConfig(level=logging.INFO)


def test_df():
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
    # (datetime=True is implicit when raw time reports are requested)
    assert sumdf.index.name == "DATE"
    assert sumdf.index.dtype == "datetime64[ns]" or sumdf.index.dtype == "datetime64"

    # Metadata should be attached using the attrs attribute on a Pandas
    # Dataframe (considered experimental by Pandas)
    assert "meta" in sumdf.attrs
    assert sumdf.attrs["meta"]["FOPR"]["unit"] == "SM3/DAY"


def test_df_column_keys():
    """Test that we can slice the dataframe on columns"""
    sumdf = summary.df(EclFiles(DATAFILE), column_keys="FOPT")
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
    sumdf = summary.df(EclFiles(DATAFILE), column_keys="FOP*")
    assert set(sumdf.columns) == fop_cols
    assert set(sumdf.attrs["meta"].keys()) == fop_cols

    sumdf = summary.df(EclFiles(DATAFILE), column_keys=["FOP*"])
    assert set(sumdf.columns) == fop_cols
    assert set(sumdf.attrs["meta"].keys()) == fop_cols

    sumdf = summary.df(EclFiles(DATAFILE), column_keys=["FOPR", "FOPT"])
    assert set(sumdf.columns) == {"FOPT", "FOPR"}
    assert set(sumdf.attrs["meta"].keys()) == {"FOPT", "FOPR"}


def test_summary2df_dates(caplog):
    """Test that we have some API possibilities with ISO dates"""
    eclfiles = EclFiles(DATAFILE)

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
    # Pandas' csv export writes datetime64 as pure date
    # when there are no clock-times involved:
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
    # realization-0 here has its last summary date at 2003-01-02
    eclfiles = EclFiles(DATAFILE)
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
    eclfiles = EclFiles(DATAFILE)
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


def test_foreseeable_future(tmpdir):
    """The foreseeable future in reservoir simulation is "defined" as 500 years.

    Check that we support summary files with this timespan"""
    tmpdir.chdir()
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
            datetime.datetime(2000, 1, 1),
            # This discrepancy is due to seconds as a 32-bit float
            # having an accuracy limit (roundoff-error)
            # https://github.com/equinor/ecl/issues/803
            datetime.datetime(2499, 12, 31, 23, 55, 44),
        ]
    ).all()

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
    assert dframe.index[-1] == datetime.datetime(2068, 12, 31, 23, 57, 52)

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
    assert dframe.index[-1] == datetime.datetime(2468, 1, 1, 0, 0, 0)


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

    assert resample_smry_dates(ecldates, freq="2001-04-05") == [
        datetime.datetime(2001, 4, 5, 0, 0)
    ]
    assert resample_smry_dates(ecldates, freq=datetime.date(2001, 4, 5)) == [
        datetime.date(2001, 4, 5)
    ]
    assert resample_smry_dates(ecldates, freq=datetime.datetime(2001, 4, 5, 0, 0)) == [
        datetime.datetime(2001, 4, 5, 0, 0)
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


def test_smry_meta():
    """Test obtaining metadata dictionary for summary vectors from an EclSum object"""
    meta = smry_meta(EclFiles(DATAFILE))

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
            pd.DataFrame(
                [{"FOPT": 1}], index=[datetime.datetime(2516, 1, 1)]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame([{"DATE": np.datetime64("2016-01-01"), "FOPT": 1}]),
            pd.DataFrame(
                [{"FOPT": 1}], index=[datetime.datetime(2016, 1, 1)]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [{"DATE": pd.Timestamp(datetime.date(2016, 1, 1)), "FOPT": 1}]
            ),
            pd.DataFrame(
                [{"FOPT": 1}], index=[datetime.datetime(2016, 1, 1)]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            pd.DataFrame(
                [
                    {
                        "DATE": datetime.datetime(2016, 1, 1, 12, 34, 56),
                        "FOPT": 1,
                    }
                ]
            ),
            pd.DataFrame(
                [{"FOPT": 1}], index=[datetime.datetime(2016, 1, 1, 12, 34, 56)]
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
            pd.DataFrame([{"DATE": datetime.date(2017, 1, 1), "FOPT": 1}]),
            pd.DataFrame(
                [{"FOPT": 1}], index=[datetime.datetime(2017, 1, 1)]
            ).rename_axis("DATE"),
        ),
        # # # # # # # # # # # # # # # # # # # # # # # #
        (
            # Dates that go beyond Pandas' datetime64[ns] limits:
            pd.DataFrame([{"DATE": datetime.date(2517, 1, 1), "FOPT": 1}]),
            pd.DataFrame(
                [{"FOPT": 1}], index=[datetime.datetime(2517, 1, 1)]
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


def test_ecl2df_errors(tmpdir):
    """Test error handling on bogus/corrupted summary files"""
    tmpdir.chdir()
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
def test_csv2ecl_summary(tmpdir, mocker):
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
            "-v",
            "summary.csv",
            "--output",
            str(Path("foo") / Path("SYNTHETIC")),
        ],
    )
    csv2ecl.main()
    assert ("foo" / Path("SYNTHETIC.UNSMRY")).is_file()
    assert ("foo" / Path("SYNTHETIC.SMSPEC")).is_file()
