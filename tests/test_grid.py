"""Test module for ecl2df.grid"""

import sys
import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import pytest

from ecl2df import grid, common
from ecl2df import ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_gridgeometry2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    grid_geom = grid.gridgeometry2df(eclfiles)

    assert isinstance(grid_geom, pd.DataFrame)
    assert not grid_geom.empty

    assert "I" in grid_geom
    assert "J" in grid_geom
    assert "K" in grid_geom
    assert "X" in grid_geom
    assert "Y" in grid_geom
    assert "Z" in grid_geom
    assert "Z_MIN" in grid_geom
    assert "Z_MAX" in grid_geom
    assert "VOLUME" in grid_geom
    assert "ZONE" in grid_geom
    assert "GLOBAL_INDEX" in grid_geom

    # If at least one inactive cell, this will hold:
    assert grid_geom["GLOBAL_INDEX"].max() > len(grid_geom)

    assert (grid_geom["Z_MAX"] > grid_geom["Z_MIN"]).all()


def test_wrongfile():
    """Test the EclFiles object on nonexistent files"""
    # pylint: disable=invalid-name,redefined-builtin

    # We can initalize this object with bogus:
    eclfiles = EclFiles("FOO.DATA")
    # but when we try to use it, things should fail:
    with pytest.raises(FileNotFoundError):
        grid.init2df(eclfiles)


def test_gridzonemap():
    """Check that zonemap can be merged automatically be default, and also
    that there is some API for supplying the zonemap directly as a dictionary"""
    eclfiles = EclFiles(DATAFILE)
    grid_geom = grid.gridgeometry2df(eclfiles, zonemap=None)

    default_zonemap = grid_geom["ZONE"]

    grid_no_zone = grid.gridgeometry2df(eclfiles, zonemap={})
    assert "ZONE" not in grid_no_zone

    assert (grid.df(eclfiles, zonemap=None)["ZONE"] == default_zonemap).all()

    df_no_zone = grid.df(eclfiles, zonemap={})
    assert "ZONE" not in df_no_zone

    df_custom_zone = grid.gridgeometry2df(eclfiles, zonemap={1: "FIRSTLAYER"})
    assert "ZONE" in df_custom_zone
    assert set(df_custom_zone[df_custom_zone["K"] == 1]["ZONE"].unique()) == set(
        ["FIRSTLAYER"]
    )
    assert len(df_custom_zone) == len(grid_no_zone)

    df_bogus_zones = grid.gridgeometry2df(
        eclfiles, zonemap={999999: "nonexistinglayer"}
    )
    assert pd.isnull(df_bogus_zones["ZONE"]).all()

    # Test a custom "subzone" map via direct usage of merge_zone on an dataframe
    # where ZONE already exists:

    dframe = grid.df(eclfiles)
    subzonemap = {1: "SUBZONE1", 2: "SUBZONE2"}
    dframe = common.merge_zones(dframe, subzonemap, zoneheader="SUBZONE", kname="K")
    assert (dframe["ZONE"] == default_zonemap).all()
    assert set(dframe[dframe["K"] == 1]["SUBZONE"].unique()) == set(["SUBZONE1"])
    assert set(dframe[dframe["K"] == 2]["SUBZONE"].unique()) == set(["SUBZONE2"])
    assert len(dframe) == len(grid_no_zone)


def test_init2df():
    """Test that dataframe with INIT vectors can be produced"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid.init2df(eclfiles)

    assert isinstance(init_df, pd.DataFrame)
    assert not init_df.empty
    assert "PERMX" in init_df
    assert "PORO" in init_df
    assert "PORV" in init_df

    # The KRO data from the INIT file contains only NaN's,
    # but libecl gives out a large negative integer/float.
    # ecl2df should ensure this comes out as a NaN (but it
    # should be allowed later to drop columns which have only NaNs))
    if "KRO" in init_df:
        assert np.isnan(init_df["KRO"].unique()).all()


def test_grid_df():
    """Test that dataframe with INIT vectors and coordinates can be produced"""
    eclfiles = EclFiles(DATAFILE)
    grid_df = grid.df(eclfiles)

    assert isinstance(grid_df, pd.DataFrame)
    assert not grid_df.empty
    assert "PERMX" in grid_df
    assert "PORO" in grid_df
    assert "PORV" in grid_df
    assert "I" in grid_df
    assert "J" in grid_df
    assert "K" in grid_df
    assert "X" in grid_df
    assert "Y" in grid_df
    assert "Z" in grid_df
    assert "VOLUME" in grid_df

    # Check that PORV is sensible
    assert (
        abs(sum(grid_df["PORO"] * grid_df["VOLUME"] - grid_df["PORV"]))
        / sum(grid_df["PORV"])
        < 0.00001
    )


def test_df2ecl(tmpdir):
    """Test if we are able to output include files for grid data"""
    eclfiles = EclFiles(DATAFILE)
    grid_df = grid.df(eclfiles)

    fipnum_str = grid.df2ecl(grid_df, "FIPNUM", dtype=int)
    assert "FIPNUM" in fipnum_str
    assert "-- Output file printed by ecl2df.grid" in fipnum_str
    assert "35817 active cells" in fipnum_str  # (comment at the end)
    assert "35840 total cell count" in fipnum_str  # (comment at the end)
    assert len(fipnum_str) > 100

    fipnum_str_nocomment = grid.df2ecl(grid_df, "FIPNUM", dtype=int, nocomments=True)
    assert "--" not in fipnum_str_nocomment
    fipnum2_str = grid.df2ecl(
        grid_df, "FIPNUM", dtype=int, eclfiles=eclfiles, nocomments=True
    )
    # This would mean that we guessed the correct global size in the first run
    assert fipnum_str_nocomment == fipnum2_str

    float_fipnum_str = grid.df2ecl(grid_df, "FIPNUM", dtype=float)
    assert len(float_fipnum_str) > len(fipnum_str)  # lots of .0 in the string.

    fipsatnum_str = grid.df2ecl(grid_df, ["FIPNUM", "SATNUM"], dtype=int)
    assert "FIPNUM" in fipsatnum_str
    assert "SATNUM" in fipsatnum_str

    grid_df["FIPNUM"] = grid_df["FIPNUM"] * 3333
    fipnum_big_str = grid.df2ecl(grid_df, "FIPNUM", dtype=int)
    assert "3333" in fipnum_big_str
    assert len(fipnum_big_str) > len(fipnum_str)

    tmpdir.chdir()
    grid.df2ecl(grid_df, ["PERMX", "PERMY", "PERMZ"], dtype=float, filename="perm.inc")
    assert Path("perm.inc").is_file()
    incstring = open("perm.inc").readlines()
    assert sum([1 for line in incstring if "PERM" in line]) == 6

    with pytest.raises(ValueError):
        grid.df2ecl(grid_df, ["PERMRR"])

    # Check when we have restart info included:
    gr_rst = grid.df(eclfiles, rstdates="all")
    fipnum_str_rst = grid.df2ecl(gr_rst, "FIPNUM", dtype=int, nocomments=True)
    assert fipnum_str_rst == fipnum_str_nocomment

    # When dates are stacked, there are NaN's  in the FIPNUM column,
    # which should be gracefully ignored.
    gr_rst_stacked = grid.df(eclfiles, rstdates="all", stackdates=True)
    fipnum_str_rst = grid.df2ecl(gr_rst_stacked, "FIPNUM", dtype=int, nocomments=True)
    assert fipnum_str_rst == fipnum_str_nocomment


def test_df2ecl_mock():
    """Test that we can use df2ecl for mocked minimal dataframes"""
    a_grid = pd.DataFrame(columns=["FIPNUM"], data=[[1], [2], [3]])
    simple_fipnum_inc = grid.df2ecl(
        a_grid, keywords="FIPNUM", dtype=int, nocomments=True
    )
    # (A warning is printed, that warning is warranted)
    assert "FIPNUM" in simple_fipnum_inc
    assert len(simple_fipnum_inc.replace("\n", " ").split()) == 5


def test_subvectors():
    """Test that we can ask for a few vectors only"""
    eclfiles = EclFiles(DATAFILE)
    init_df = grid.init2df(eclfiles, "PORO")
    assert "PORO" in init_df
    assert "PERMX" not in init_df
    assert "PORV" not in init_df

    init_df = grid.init2df(eclfiles, "P*")
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" not in init_df

    init_df = grid.init2df(eclfiles, ["P*"])
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" not in init_df

    init_df = grid.init2df(eclfiles, ["P*", "*NUM"])
    assert "PORO" in init_df
    assert "PERMX" in init_df
    assert "PVTNUM" in init_df
    assert "SATNUM" in init_df
    assert "MULTZ" not in init_df


def test_dropconstants():
    """Test dropping of constants columns from dataframes"""
    df = pd.DataFrame(columns=["A", "B"], data=[[1, 1], [2, 1]])
    assert "B" not in grid.drop_constant_columns(df)
    assert "A" in grid.drop_constant_columns(df)
    assert "B" in grid.drop_constant_columns(df, alwayskeep="B")
    assert "B" in grid.drop_constant_columns(df, alwayskeep=["B"])


def test_df():
    """Test the df function"""
    eclfiles = EclFiles(DATAFILE)
    # assert error..
    with pytest.raises(TypeError):
        # pylint: disable=no-value-for-parameter
        grid.df()

    grid_df = grid.df(eclfiles)
    assert not grid_df.empty
    assert "I" in grid_df  # From GRID
    assert "PORO" in grid_df  # From INIT
    assert "SOIL" not in grid_df  # We do not get RST unless we ask for it.

    grid_df = grid.df(eclfiles, vectors="*")
    assert "I" in grid_df  # From GRID
    assert "PORO" in grid_df  # From INIT
    assert "SOIL" not in grid_df  # We do not get RST unless we ask for it.

    grid_df = grid.df(eclfiles, vectors=["*"])
    assert "I" in grid_df  # From GRID
    assert "PORO" in grid_df  # From INIT
    assert "SOIL" not in grid_df  # We do not get RST unless we ask for it.

    grid_df = grid.df(eclfiles, vectors="PRESSURE")
    assert "I" in grid_df
    assert "PRESSURE" not in grid_df  # that vector is only in RST
    assert len(grid_df) == 35817
    assert "VOLUME" in grid_df

    grid_df = grid.df(eclfiles, vectors=["PRESSURE"])
    assert "I" in grid_df
    assert not grid_df.empty
    assert "PRESSURE" not in grid_df
    geometry_cols = len(grid_df.columns)

    grid_df = grid.df(eclfiles, vectors=["PRESSURE"], rstdates="last", stackdates=True)
    assert "PRESSURE" in grid_df
    assert len(grid_df.columns) == geometry_cols + 2
    assert "DATE" in grid_df  # Present because of stackdates

    grid_df = grid.df(eclfiles, vectors="PRESSURE", rstdates="last")
    assert "PRESSURE" in grid_df
    assert len(grid_df.columns) == geometry_cols + 1

    grid_df = grid.df(eclfiles, vectors="PRESSURE", rstdates="last", dateinheaders=True)
    assert "PRESSURE" not in grid_df
    assert "PRESSURE@2001-08-01" in grid_df

    grid_df = grid.df(
        eclfiles, vectors=["PORO", "PRESSURE"], rstdates="all", stackdates=True
    )
    assert "PRESSURE" in grid_df
    assert len(grid_df.columns) == geometry_cols + 3
    assert "DATE" in grid_df
    assert len(grid_df["DATE"].unique()) == 4
    assert not grid_df.isna().any().any()
    # Check that all but the dynamic data has been repeated:
    df1 = (
        grid_df[grid_df["DATE"] == "2000-01-01"]
        .drop(["DATE", "PRESSURE"], axis=1)
        .reset_index(drop=True)
    )
    df2 = (
        grid_df[grid_df["DATE"] == "2000-07-01"]
        .drop(["PRESSURE", "DATE"], axis=1)
        .reset_index(drop=True)
    )
    df3 = (
        grid_df[grid_df["DATE"] == "2001-02-01"]
        .drop(["PRESSURE", "DATE"], axis=1)
        .reset_index(drop=True)
    )
    df4 = (
        grid_df[grid_df["DATE"] == "2001-08-01"]
        .drop(["PRESSURE", "DATE"], axis=1)
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(df1, df2)
    pd.testing.assert_frame_equal(df1, df3)
    pd.testing.assert_frame_equal(df1, df4)

    grid_df = grid.df(eclfiles, vectors="PORO")
    assert "I" in grid_df
    assert "PORO" in grid_df
    assert len(grid_df) == 35817
    assert "DATE" not in grid_df

    grid_df = grid.df(eclfiles, vectors="PORO", rstdates="all")
    assert "I" in grid_df
    assert "PORO" in grid_df
    assert "DATE" not in grid_df
    # (no RST columns, so no DATE info in the dataframe)
    # (warnings should be printed)

    grid_df = grid.df(eclfiles, vectors="PORO", rstdates="all", stackdates=True)
    assert "I" in grid_df
    assert "PORO" in grid_df
    assert "DATE" not in grid_df
    # DATE is not included as it really does not make sense. The code
    # could have multiplied up the static dataframe each tagged with a date
    # but not for now.


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir / "eclgrid.csv"
    sys.argv = [
        "ecl2csv",
        "grid",
        DATAFILE,
        "-o",
        str(tmpcsvfile),
        "--rstdates",
        "first",
        "--vectors",
        "PORO",
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    Path(tmpcsvfile).unlink()

    # Do again with also restarts and multiple vectors:
    sys.argv = [
        "ecl2csv",
        "grid",
        DATAFILE,
        "-o",
        str(tmpcsvfile),
        "--rstdates",
        "2001-02-01",
        "--vectors",
        "PORO",
        "PERMX",
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
    assert "PORO" in disk_df
    assert "PERMX" in disk_df
    Path(tmpcsvfile).unlink()

    # Test with constants dropping
    sys.argv = ["ecl2csv", "grid", DATAFILE, "-o", str(tmpcsvfile), "--dropconstants"]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    # That PVTNUM is constant is a particular feature
    # of the test dataset.
    assert "PVTNUM" not in disk_df
    assert not disk_df.empty


def test_get_available_rst_dates():
    """Test the support of dates in restart files"""
    eclfiles = EclFiles(DATAFILE)
    # rstfile = eclfiles.get_rstfile()

    alldates = grid.get_available_rst_dates(eclfiles)
    assert len(alldates) == 4

    didx = grid.dates2rstindices(eclfiles, "all")
    assert len(didx[0]) == len(alldates)
    assert len(didx[1]) == len(alldates)
    assert isinstance(didx[0][0], int)
    assert isinstance(didx[1][0], datetime.date)
    assert didx[1][0] == alldates[0]
    assert didx[1][-1] == alldates[-1]

    first = grid.dates2rstindices(eclfiles, "first")
    assert first[1][0] == alldates[0]

    last = grid.dates2rstindices(eclfiles, "last")
    assert last[1][0] == alldates[-1]

    dates = grid.get_available_rst_dates(eclfiles)
    assert isinstance(dates, list)

    # Test with missing RST file:
    eclfiles = EclFiles("BOGUS.DATA")
    with pytest.raises(IOError):
        eclfiles.get_rstfile()


def test_rst2df():
    """Test producing dataframes from restart files"""
    eclfiles = EclFiles(DATAFILE)
    assert grid.rst2df(eclfiles, "first").shape == (35817, 24)
    assert grid.rst2df(eclfiles, "last").shape == (35817, 24)
    assert grid.rst2df(eclfiles, "all").shape == (35817, 23 * 4 + 1)

    assert "SOIL" in grid.rst2df(eclfiles, date="first", dateinheaders=False)
    assert (
        "SOIL@2000-01-01" in grid.rst2df(eclfiles, "first", dateinheaders=True).columns
    )

    rst_df = grid.rst2df(eclfiles, "first", stackdates=True)
    assert "DATE" in rst_df
    assert rst_df["DATE"].unique()[0] == "2000-01-01"
    rst_df = grid.rst2df(eclfiles, "all", stackdates=True)
    assert len(rst_df["DATE"].unique()) == len(grid.get_available_rst_dates(eclfiles))

    # "DATE" and "active" are now the extra columns:
    assert rst_df.shape == (4 * 35817, 23 + 2)

    # Test that only the PPCW column contains NaN's (only defined for selected cells)
    nancols = rst_df.isna().any()
    assert nancols["PPCW"]
    assert (
        len(rst_df[["PPCW", "DATE"]].dropna()["DATE"].unique()) == 4
    )  # All dates present
    assert sum(nancols) == 1  # All other columns are "False"

    # Check vector slicing:
    rst_df = grid.rst2df(eclfiles, "first", vectors="S???")
    assert rst_df.shape == (35817, 4)
    assert "SGAS" in rst_df
    assert "SWAT" in rst_df
    assert "SOIL" in rst_df  # This is actually computed
    assert "FIPWAT" not in rst_df

    rst_df = grid.rst2df(eclfiles, "first", vectors=["PRESSURE", "SWAT"])
    assert "PRESSURE" in rst_df
    assert "SWAT" in rst_df
    assert "SGAS" not in rst_df
    assert "SOIL" not in rst_df

    # Check that we can avoid getting SOIL if we are explicit:
    rst_df = grid.rst2df(eclfiles, "first", vectors=["SGAS", "SWAT"])
    assert "SOIL" not in rst_df
    assert "SGAS" in rst_df
    assert "SWAT" in rst_df
