"""Test module for ecl2df.pillars"""

from pathlib import Path

import pandas as pd
import pytest

from ecl2df import ecl2csv, grid, pillars
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_pillars():
    """Test that we can build a dataframe of pillar statistics"""
    eclfiles = EclFiles(REEK)
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

    # Grouping by unknowns only trigger a warning
    pd.testing.assert_frame_equal(
        pillars.df(eclfiles), pillars.df(eclfiles, region="FOOBAR")
    )


# These frame will be reused in the following test.
PILLARS_WITH_UPFLANK = pd.DataFrame(
    columns=["PILLAR", "SWAT", "SOIL", "Z"],
    data=[
        ["1-1", 0.2, 0.8, 950],
        ["1-1", 0.7, 0.3, 951],
        ["1-1", 0.9, 0.1, 952],
        ["1-1", 1, 0, 953],
        ["2-1", 0.2, 1, 400],  # Upflank oil, to be ignored.
    ],
)
PILLARS_GAS_IN_WATER = pd.DataFrame(
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


@pytest.mark.parametrize(
    "pillar_df, args, expectedrows",
    [
        (pd.DataFrame(), {}, []),
        pytest.param(
            pd.DataFrame([{"SWAT": 1}]),
            {},
            None,
            marks=pytest.mark.xfail(raises=KeyError),
            id="no_pillar_column",
        ),
        pytest.param(
            pd.DataFrame([{"SWAT": 1, "I": 1, "J": 1}]),
            {},
            None,
            marks=pytest.mark.xfail(raises=KeyError),
            id="no_z_column",
        ),
        pytest.param(
            pd.DataFrame([{"SWAT": 1, "I": 1, "J": 1, "Z": 1000}]),
            {},
            [],
            id="no_saturations_gives_empty_result",
        ),
        (
            pd.DataFrame(
                columns=["PILLAR", "SWAT", "SOIL", "SGAS", "Z"],
                data=[["1-1", 1, 0, 0, 1000]],
            ),
            {},
            [],
        ),
        (
            pd.DataFrame(
                columns=["PILLAR", "SWAT", "SOIL", "SGAS", "Z"],
                data=[["1-1", 1, 0, 0, 1000], ["1-1", 0.5, 0.5, 0, 999]],
            ),
            {},
            [{"PILLAR": "1-1", "OWC": 999}],
        ),
        (
            pd.DataFrame(
                columns=["PILLAR", "SWAT", "SOIL", "SGAS", "Z"],
                data=[["1-1", 1, 0, 0, 1000], ["1-1", 0.5, 0.5, 0, 999]],
            ),
            {"soilcutoff": 0.2},
            [{"PILLAR": "1-1", "OWC": 999}],
        ),
        pytest.param(
            pd.DataFrame(
                columns=["PILLAR", "SWAT", "SOIL", "SGAS", "Z"],
                data=[["1-1", 1, 0, 0, 1000], ["1-1", 0.5, 0.5, 0, 999]],
            ),
            {"soilcutoff": 0.6},
            [],
            id="bump_soilcutoff_giving_no_contact",
        ),
        pytest.param(
            pd.DataFrame(
                columns=["PILLAR", "SWAT", "SGAS", "Z"],
                data=[["1-1", 1, 0, 1000], ["1-1", 0.2, 0.8, 999]],
            ),
            {},
            [{"PILLAR": "1-1", "GWC": 999}],
            id="two-phase_gas-water",
        ),
        pytest.param(
            pd.DataFrame(
                columns=["PILLAR", "SWAT", "SOIL", "Z"],
                data=[["1-1", 1, 0, 1000], ["1-1", 0.2, 0.8, 999]],
            ),
            {},
            [{"PILLAR": "1-1", "OWC": 999}],
            id="two-phase-oil-water",
        ),
        pytest.param(
            pd.DataFrame(
                columns=["PILLAR", "EQLNUM", "SWAT", "SOIL", "Z"],
                data=[
                    ["1-1", 1, 1, 0, 1000],
                    ["1-1", 1, 0.2, 0.8, 999],
                    ["1-1", 2, 1, 0, 2000],
                    ["1-1", 2, 0.2, 0.8, 1999],
                ],
            ),
            {"region": "EQLNUM"},
            [
                {"PILLAR": "1-1", "EQLNUM": 1, "OWC": 999},
                {"PILLAR": "1-1", "EQLNUM": 2, "OWC": 1999},
            ],
            id="testing_region_support",
        ),
        pytest.param(
            PILLARS_WITH_UPFLANK,
            {},
            [
                {"PILLAR": "1-1", "OWC": 951},
            ],
            id="upflank_oil_ignored",
        ),
        pytest.param(
            PILLARS_WITH_UPFLANK,
            {"swatcutoff": 0.05},
            [
                {"PILLAR": "1-1", "OWC": 951},
                {"PILLAR": "2-1", "OWC": 400},
            ],
            id="swatcutoff_includes_upflank",
        ),
        # "OWC is deepest cell centre with saturation more than soilcutoff":
        pytest.param(
            PILLARS_WITH_UPFLANK,
            {"soilcutoff": 0.05},
            [
                {"PILLAR": "1-1", "OWC": 952},
            ],
            id="soilcutoff_0.05",
        ),
        pytest.param(
            PILLARS_WITH_UPFLANK,
            {"soilcutoff": 0.25},
            [
                {"PILLAR": "1-1", "OWC": 951},
            ],
            id="soilcutoff_0.25",
        ),
        pytest.param(
            PILLARS_WITH_UPFLANK,
            {"soilcutoff": 0.7},
            [
                {"PILLAR": "1-1", "OWC": 950},
            ],
            id="soilcutoff_0.7",
        ),
        pytest.param(
            PILLARS_WITH_UPFLANK,
            {"soilcutoff": 0.8},
            [],
            id="soilcutoff_0.8",
        ),
        # "GOC is deepest point with gas saturation is more than sgascutoff,
        # and where some cells have oil saturation more than gocsoilcutoff"
        pytest.param(
            PILLARS_GAS_IN_WATER,
            {},
            [{"PILLAR": "1-1", "OWC": 951, "GOC": 940}],
            id="goc_gas_in_water",
        ),
        pytest.param(
            PILLARS_GAS_IN_WATER,
            {"sgascutoff": 0.05},
            [{"PILLAR": "1-1", "OWC": 951, "GOC": 945}],
            id="sgascutoff_0.05",
        ),
        pytest.param(
            PILLARS_GAS_IN_WATER,
            {"sgascutoff": 0.4},
            [{"PILLAR": "1-1", "OWC": 951, "GOC": 942}],
            id="sgascutoff_0.4",
        ),
        pytest.param(
            PILLARS_GAS_IN_WATER,
            {"sgascutoff": 0.75},
            [{"PILLAR": "1-1", "OWC": 951, "GOC": 940}],
            id="sgascutoff_0.75",
        ),
    ],
)
def test_compute_pillar_contacts(pillar_df, args, expectedrows):
    pd.testing.assert_frame_equal(
        pillars.compute_pillar_contacts(pillar_df, **args), pd.DataFrame(expectedrows)
    )


@pytest.mark.parametrize(
    "dframe, datestr, expectedrows",
    [
        (pd.DataFrame(), None, []),
        (
            pd.DataFrame([{"PORV": 1, "SWAT": 0.9, "SGAS": 0}]),
            None,
            [{"SOIL": 0.1, "WATVOL": 0.9, "GASVOL": 0, "OILVOL": 0.1}],
        ),
        (
            # Empty datestring is the same as None:
            pd.DataFrame([{"PORV": 1, "SWAT": 0.9, "SGAS": 0}]),
            "",
            [{"SOIL": 0.1, "WATVOL": 0.9, "GASVOL": 0, "OILVOL": 0.1}],
        ),
        (
            # With a date included:
            pd.DataFrame([{"PORV": 1, "SWAT@2000-01-01": 0.9, "SGAS@2000-01-01": 0}]),
            "2000-01-01",
            [
                {
                    "SOIL@2000-01-01": 0.1,
                    "WATVOL@2000-01-01": 0.9,
                    "GASVOL@2000-01-01": 0,
                    "OILVOL@2000-01-01": 0.1,
                }
            ],
        ),
        (
            # Asking for a date for which there is no data:
            pd.DataFrame([{"PORV": 1, "SWAT@2000-01-01": 0.9, "SGAS@2000-01-01": 0}]),
            "2001-01-01",
            [],
        ),
        (
            # Two phase oil-water
            pd.DataFrame([{"PORV": 1, "SWAT": 0.9}]),
            None,
            [{"SOIL": 0.1, "WATVOL": 0.9, "OILVOL": 0.1}],
        ),
        (
            # Including surface conditions
            pd.DataFrame(
                [{"PORV": 1, "SWAT": 0.5, "SGAS": 0.2, "1OVERBO": 0.8, "1OVERBG": 2}]
            ),
            None,
            [
                {
                    "SOIL": 0.3,
                    "WATVOL": 0.5,
                    "GASVOL": 0.2,
                    "OILVOL": 0.3,
                    "OILVOLSURF": 0.3 * 0.8,
                    "GASVOLSURF": 0.2 * 2,
                }
            ],
        ),
    ],
)
def test_compute_volumes(dframe, datestr, expectedrows):
    pd.testing.assert_frame_equal(
        pillars.compute_volumes(dframe, datestr), pd.DataFrame(expectedrows)
    )


def test_main(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / "pillars.csv"
    mocker.patch("sys.argv", ["ecl2csv", "pillars", REEK, "-o", str(tmpcsvfile)])
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" in disk_df
    assert not disk_df.empty
    assert len(disk_df) == 2560

    # Group over every pillar, no matter what FIPNUM. One single row output
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "",
            "--group",
            "-o",
            str(tmpcsvfile),
        ],
    )
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
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "FIPNUM",
            "-o",
            str(tmpcsvfile),
        ],
    )
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" in disk_df
    assert "FIPNUM" in disk_df
    assert "EQLNUM" not in disk_df
    assert len(disk_df) == 7675

    # Group pr. FIPNUM:
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "FIPNUM",
            "--group",
            "-o",
            str(tmpcsvfile),
        ],
    )
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert "PILLAR" not in disk_df  # because of grouping
    assert "FIPNUM" in disk_df  # grouped by this.
    assert len(disk_df) == 6

    # Test dates:
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "",
            "--group",
            "--rstdates",
            "first",
            "-o",
            str(tmpcsvfile),
        ],
    )
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
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "",
            "--group",
            "--rstdates",
            "last",
            "-o",
            str(tmpcsvfile),
        ],
    )
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
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "",
            "--group",
            "--rstdates",
            "all",
            "-o",
            str(tmpcsvfile),
        ],
    )
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
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "",
            "--group",
            "--rstdates",
            "all",
            "--stackdates",
            "-o",
            str(tmpcsvfile),
        ],
    )
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
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            REEK,
            "--region",
            "FIPNUM",
            "--rstdates",
            "all",
            "--stackdates",
            "-o",
            str(tmpcsvfile),
        ],
    )
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
    mocker.patch(
        "sys.argv",
        [
            "ecl2csv",
            "pillars",
            "-v",
            REEK,
            "--rstdates",
            "all",
            "--stackdates",
            "-o",
            str(tmpcsvfile),
        ],
    )
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
