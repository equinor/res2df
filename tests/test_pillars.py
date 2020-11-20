"""Test module for ecl2df.pillars"""

import sys
from pathlib import Path

import pandas as pd

from ecl2df import pillars
from ecl2df import grid
from ecl2df import ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_pillars():
    """Test that we can build a dataframe of pillar statistics"""
    eclfiles = EclFiles(DATAFILE)
    pillars_df = pillars.df(eclfiles)
    assert "PILLAR" in pillars_df
    assert "VOLUME" in pillars_df
    assert "PORV" in pillars_df
    assert "PERMX" in pillars_df
    assert "X" in pillars_df
    assert "Y" in pillars_df
    assert "PORO" in pillars_df
    assert "OILVOL" not in pillars_df
    assert "FIPNUM" not in pillars_df
    assert "EQLNUM" not in pillars_df
    assert "OWC" not in pillars_df
    assert "GOC" not in pillars_df
    assert len(pillars_df) == 2560

    pillars_df = pillars.df(eclfiles, region="FIPNUM")
    assert "FIPNUM" in pillars_df
    assert len(pillars_df["FIPNUM"].unique()) == 6
    assert "OILVOL" not in pillars_df

    pillars_df = pillars.df(eclfiles, rstdates="first")
    firstdate = str(grid.dates2rstindices(eclfiles, "first")[1][0])
    assert "OILVOL@" + firstdate in pillars_df
    assert "GASVOL@" + firstdate in pillars_df
    assert "WATVOL@" + firstdate in pillars_df

    pillars_df = pillars.df(eclfiles, rstdates="last", soilcutoff=0.2, sgascutoff=0.2)
    lastdate = str(grid.dates2rstindices(eclfiles, "last")[1][0])
    assert "OWC@" + lastdate in pillars_df
    assert "GOC@" + lastdate not in pillars_df  # Because the dataset has no GAS...


def test_contact():
    """Test the contact estimation on mocked grid frames

    I, J, and K are not included in the mock frames, as they are not
    necessary.
    """
    gdf = pd.DataFrame(
        columns=["PILLAR", "SWAT", "SOIL", "SGAS", "Z"], data=[["1-1", 1, 0, 0, 1000]]
    )
    gdf_contacts = pillars.compute_pillar_contacts(gdf)
    assert gdf_contacts.empty

    gdf = pd.DataFrame(
        columns=["PILLAR", "SWAT", "SOIL", "SGAS", "Z"],
        data=[["1-1", 1, 0, 0, 1000], ["1-1", 0.5, 0.5, 0, 999]],
    )
    gdf_contact = pillars.compute_pillar_contacts(gdf, soilcutoff=0.2)
    assert not gdf_contact.empty
    assert gdf_contact["OWC"].values == [999]

    gdf = pd.DataFrame(
        columns=["PILLAR", "SWAT", "SGAS", "Z"],
        data=[["1-1", 1, 0, 1000], ["1-1", 0.2, 0.8, 999]],
    )
    gdf_contact = pillars.compute_pillar_contacts(gdf)
    assert not gdf_contact.empty
    assert gdf_contact["GWC"].values == [999]

    gdf = pd.DataFrame(
        columns=["PILLAR", "SWAT", "SOIL", "Z"],
        data=[["1-1", 1, 0, 1000], ["1-1", 0.2, 0.8, 999]],
    )
    gdf_contact = pillars.compute_pillar_contacts(gdf)
    assert not gdf_contact.empty
    assert gdf_contact["OWC"].values == [999]

    gdf = pd.DataFrame(
        columns=["PILLAR", "EQLNUM", "SWAT", "SOIL", "Z"],
        data=[
            ["1-1", 1, 1, 0, 1000],
            ["1-1", 1, 0.2, 0.8, 999],
            ["1-1", 2, 1, 0, 2000],
            ["1-1", 2, 0.2, 0.8, 1999],
        ],
    )
    gdf_contact = pillars.compute_pillar_contacts(gdf, region="EQLNUM")
    assert not gdf_contact.empty
    assert len(gdf_contact) == 2
    assert 999 in gdf_contact["OWC"].values
    assert 1999 in gdf_contact["OWC"].values

    gdf = pd.DataFrame(
        columns=["PILLAR", "SWAT", "SOIL", "Z"],
        data=[
            ["1-1", 0.2, 0.8, 950],
            ["1-1", 0.7, 0.3, 951],
            ["1-1", 0.9, 0.1, 952],
            ["1-1", 1, 0, 953],
            ["2-1", 0.2, 1, 400],  # Upflank oil, to be ignored.
        ],
    )
    # swatcutoff controls the upflank oil:
    assert len(pillars.compute_pillar_contacts(gdf)) == 1
    assert len(pillars.compute_pillar_contacts(gdf, swatcutoff=0.05)) == 2

    # "OWC is deepest cell centre with saturation more than soilcutoff"
    assert pillars.compute_pillar_contacts(gdf, soilcutoff=0.05)["OWC"].values[0] == 952
    assert pillars.compute_pillar_contacts(gdf, soilcutoff=0.25)["OWC"].values[0] == 951
    assert pillars.compute_pillar_contacts(gdf, soilcutoff=0.7)["OWC"].values[0] == 950
    assert pillars.compute_pillar_contacts(gdf, soilcutoff=0.8).empty

    gdf = pd.DataFrame(
        columns=["PILLAR", "SWAT", "SOIL", "SGAS", "Z"],
        data=[
            ["1-1", 0.2, 0.02, 0.8, 940],
            ["1-1", 0.2, 0.1, 0.7, 942],
            ["1-1", 0.2, 0.4, 0.4, 945],
            ["1-1", 0.2, 0.8, 0, 950],
            ["1-1", 0.7, 0.3, 0, 951],
            ["1-1", 0.9, 0.1, 0, 952],
            ["1-1", 1, 0, 0, 953],
            # Add a row with gas saturation in water, this
            # could be due to a gas injector and
            # should not be picked up as a GOC:
            ["1-1", 0.5, 0, 0.5, 953],
            ["1-1", 1, 0, 0, 953],
        ],
    )
    # "GOC is deepest point with gas saturation is more than sgascutoff,
    # and where some cells have oil saturation more than gocsoilcutoff"
    assert pillars.compute_pillar_contacts(gdf, sgascutoff=0.05)["GOC"].values[0] == 945
    assert pillars.compute_pillar_contacts(gdf, sgascutoff=0.4)["GOC"].values[0] == 942
    assert pillars.compute_pillar_contacts(gdf, sgascutoff=0.75)["GOC"].values[0] == 940

    # Check default behaviour, this is allowed to change in the future.
    def_contacts = pillars.compute_pillar_contacts(gdf)
    assert def_contacts["OWC"].values[0] == 951
    assert def_contacts["GOC"].values[0] == 940


def test_main(tmpdir):
    """Test command line interface"""
    tmpcsvfile = tmpdir / "pillars.csv"
    sys.argv = ["ecl2csv", "pillars", DATAFILE, "-o", str(tmpcsvfile)]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" in disk_df
    assert not disk_df.empty
    assert len(disk_df) == 2560

    # Group over every pillar, no matter what FIPNUM. One single row output
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "",
        "--group",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" not in disk_df  # because of grouping
    assert "FIPNUM" not in disk_df
    assert "EQLNUM" not in disk_df
    # We are getting a single row only
    assert len(disk_df) == 1
    assert not disk_df.empty

    # Pillars pr region, but no grouping
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "FIPNUM",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" in disk_df
    assert "FIPNUM" in disk_df
    assert "EQLNUM" not in disk_df
    assert len(disk_df) == 7675

    # Group pr. FIPNUM:
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "FIPNUM",
        "--group",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" not in disk_df  # because of grouping
    assert "FIPNUM" in disk_df  # grouped by this.
    assert len(disk_df) == 6

    # Test dates:
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "",
        "--group",
        "--rstdates",
        "first",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" not in disk_df  # because of region averaging
    assert "FIPNUM" not in disk_df
    assert "WATVOL@2000-01-01" in disk_df
    assert "OILVOL@2000-01-01" in disk_df
    assert "OWC@2000-01-01" in disk_df
    # Check that we don't get meaningless temporary data:
    assert "SWAT@2000-01-01" not in disk_df
    assert "SOIL@2000-01-01" not in disk_df
    assert len(disk_df) == 1

    # Test dates:
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "",
        "--group",
        "--rstdates",
        "last",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" not in disk_df  # because of region averaging
    assert "FIPNUM" not in disk_df
    assert "WATVOL@2001-08-01" in disk_df
    assert "OILVOL@2001-08-01" in disk_df
    assert "OWC@2001-08-01" in disk_df
    # Check that we don't get meaningless temporary data:
    assert "SWAT@2001-01-01" not in disk_df
    assert "SOIL@2000-01-01" not in disk_df
    assert len(disk_df) == 1

    # Test all dates:
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "",
        "--group",
        "--rstdates",
        "all",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" not in disk_df  # because of region averaging
    assert "FIPNUM" not in disk_df
    assert "WATVOL@2001-08-01" in disk_df
    assert "WATVOL@2000-07-01" in disk_df
    assert "WATVOL@2000-01-01" in disk_df
    assert "WATVOL@2001-02-01" in disk_df
    assert len(disk_df) == 1

    # Test stacked dates:
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "",
        "--group",
        "--rstdates",
        "all",
        "--stackdates",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" not in disk_df  # because of region averaging
    assert "FIPNUM" not in disk_df
    assert "WATVOL@2001-08-01" not in disk_df
    assert "WATVOL@2000-07-01" not in disk_df
    assert "WATVOL@2000-01-01" not in disk_df
    assert "WATVOL@2001-02-01" not in disk_df
    assert "WATVOL" in disk_df
    assert "DATE" in disk_df
    assert len(disk_df) == 4

    # Test stacked dates, no grouping:
    sys.argv = [
        "ecl2csv",
        "pillars",
        DATAFILE,
        "--region",
        "FIPNUM",
        "--rstdates",
        "all",
        "--stackdates",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" in disk_df
    assert "FIPNUM" in disk_df
    assert "WATVOL@2001-02-01" not in disk_df
    assert "WATVOL" in disk_df
    assert "DATE" in disk_df
    assert len(disk_df) == 30700

    # Test stacked dates but with grouping only on pillars
    sys.argv = [
        "ecl2csv",
        "pillars",
        "-v",
        DATAFILE,
        "--rstdates",
        "all",
        "--stackdates",
        "-o",
        str(tmpcsvfile),
    ]
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" in disk_df
    assert "FIPNUM" not in disk_df
    assert "WATVOL@2001-08-01" not in disk_df
    assert "WATVOL@2000-07-01" not in disk_df
    assert "WATVOL@2000-01-01" not in disk_df
    assert "WATVOL@2001-02-01" not in disk_df
    assert "WATVOL" in disk_df
    assert "OILVOL" in disk_df
    assert "DATE" in disk_df
    assert len(disk_df) == 10240 == 2560 * len(disk_df["DATE"].unique())
