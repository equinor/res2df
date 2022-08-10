from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ecl2df import common, compdat, wellcompletiondata
from ecl2df.eclfiles import EclFiles
from ecl2df.wellcompletiondata import (
    _aggregate_layer_to_zone,
    _df2pyarrow,
    _excl_well_startswith,
    _merge_compdat_and_connstatus,
)

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed",
        allow_module_level=True,
    )

TESTDIR = Path(__file__).absolute().parent
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
EIGHTCELLS_ZONEMAP = common.convert_lyrlist_to_zonemap(
    common.parse_lyrfile(str(TESTDIR / "data/eightcells/zones.lyr"))
)


def test_eightcells_with_wellconnstatus():
    """Test the Eightcells dataset with the well connection status
    option activated (connection status extracted from summary data)
    """
    eclfiles = EclFiles(EIGHTCELLS)
    expected_dframe = pd.DataFrame(
        [
            {
                "WELL": "OP1",
                "ZONE": "Upper",
                "DATE": datetime(year=2000, month=1, day=2),
                "KH": -1,
                "OP/SH": "OPEN",
            }
        ]
    )
    pd.testing.assert_frame_equal(
        wellcompletiondata.df(
            eclfiles, zonemap=EIGHTCELLS_ZONEMAP, use_wellconnstatus=True
        ),
        expected_dframe,
        check_dtype=False,
    )


def test_eightcells_without_wellconnstatus():
    """Test the Eightcells dataset with only the compdat export data (connection
    status extracted from parsing the schedule file)"""
    eclfiles = EclFiles(EIGHTCELLS)
    expected_dframe = pd.DataFrame(
        [
            {
                "WELL": "OP1",
                "ZONE": "Upper",
                "DATE": datetime(year=2000, month=1, day=1),
                "KH": -1,
                "OP/SH": "OPEN",
            }
        ]
    )
    pd.testing.assert_frame_equal(
        wellcompletiondata.df(
            eclfiles, zonemap=EIGHTCELLS_ZONEMAP, use_wellconnstatus=False
        ),
        expected_dframe,
        check_dtype=False,
    )


def test_df2pyarrow():
    """Test that dataframe is conserved using _df2pyarrow"""
    eclfiles = EclFiles(EIGHTCELLS)
    df = wellcompletiondata.df(
        eclfiles, zonemap=EIGHTCELLS_ZONEMAP, use_wellconnstatus=False
    )
    df["KH"] = df["KH"].astype(np.int32)
    pd.testing.assert_frame_equal(df, _df2pyarrow(df).to_pandas(), check_like=True)


def test_metadata():
    """Test that the KH column has metadata and that unit is mDm"""
    eclfiles = EclFiles(EIGHTCELLS)
    df = wellcompletiondata.df(
        eclfiles, zonemap=EIGHTCELLS_ZONEMAP, use_wellconnstatus=False
    )
    assert df.attrs["meta"] == {"KH": {"unit": "mDm"}}

    table = _df2pyarrow(df)
    field = table.schema.field("KH")
    assert field.metadata is not None
    assert field.metadata[b"unit"] == b"mDm"


def test_empty_zonemap():
    """Test empty zonemap and zonemap with layers that doesn't exist in the compdat
    table. Both returns an empty dataframe
    """
    eclfiles = EclFiles(EIGHTCELLS)
    df = wellcompletiondata.df(eclfiles, zonemap={}, use_wellconnstatus=False)
    assert df.empty

    zonemap = {1000: "ZONE1", -1: "ZONE1"}
    df = wellcompletiondata.df(eclfiles, zonemap=zonemap, use_wellconnstatus=False)
    assert df.empty


def test_zonemap_with_some_undefined_layers():
    """Layers in the zonemap that don't exist in the compdat output will be ignored."""
    eclfiles = EclFiles(REEK)
    zonemap = {1: "ZONE1", 2: "ZONE1"}
    df = wellcompletiondata.df(eclfiles, zonemap=zonemap, use_wellconnstatus=False)
    compdat_df = compdat.df(eclfiles)

    # Filter compdat on layer 1 and 2
    compdat_df = compdat_df[compdat_df["K1"] <= 2]

    # Check for all wells that the aggregated KH is the same as the sum of all
    # the compdat entries in the same layers
    for well, well_df in df.groupby("WELL"):
        assert (
            well_df["KH"].values[0]
            == compdat_df[compdat_df["WELL"] == well]["KH"].sum()
        )


def test_merge_compdat_and_connstatus():
    """Tests the functionality of the merge_compdat_and_connstatus function.

    The following functionality is covered:
    * The two first rows of df_compdat is replaced with the two first from
    df_connstatus, except for the KH (which is only available in df_compdat).
    KH is taken from the first of the two compdat rows
    * The A2 well is not available in df_connstatus and will be taken as is
    from df_compdat
    * the fourth row in df_compdat (WELL: A1, REAL:1) is ignored because A1 is
    in df_connstatus, but not REAL 1. We don't mix compdat and connstatus data
    for the same well
    * The fourth row in df_compdat has KH=Nan. This will be 0 in the output
    """
    df_compdat = pd.DataFrame(
        data={
            "DATE": [
                "2021-01-01",
                "2021-05-01",
                "2021-01-01",
                "2021-01-01",
                "2022-01-01",
            ],
            "REAL": [0, 0, 0, 1, 0],
            "WELL": ["A1", "A1", "A2", "A1", "A3"],
            "I": [1, 1, 1, 1, 1],
            "J": [1, 1, 1, 1, 1],
            "K1": [1, 1, 1, 1, 1],
            "OP/SH": ["SHUT", "OPEN", "OPEN", "OPEN", "OPEN"],
            "KH": [100, 1000, 10, 100, np.nan],
            "ZONE": ["ZONE1", "ZONE1", "ZONE1", "ZONE1", "ZONE1"],
        }
    )
    df_connstatus = pd.DataFrame(
        data={
            "DATE": ["2021-03-01", "2021-08-01", "2021-01-01"],
            "REAL": [0, 0, 0],
            "WELL": ["A1", "A1", "A3"],
            "I": [1, 1, 1],
            "J": [1, 1, 1],
            "K1": [1, 1, 1],
            "OP/SH": ["OPEN", "SHUT", "OPEN"],
        }
    )
    df_output = pd.DataFrame(
        data={
            "DATE": ["2021-03-01", "2021-08-01", "2021-01-01", "2021-01-01"],
            "REAL": [0, 0, 0, 0],
            "WELL": ["A1", "A1", "A3", "A2"],
            "I": [1, 1, 1, 1],
            "J": [1, 1, 1, 1],
            "K1": [1, 1, 1, 1],
            "OP/SH": ["OPEN", "SHUT", "OPEN", "OPEN"],
            "KH": [100.0, 100.0, 0.0, 10.0],
            "ZONE": ["ZONE1", "ZONE1", "ZONE1", "ZONE1"],
        }
    )
    df_compdat["DATE"] = pd.to_datetime(df_compdat["DATE"])
    df_connstatus["DATE"] = pd.to_datetime(df_connstatus["DATE"])
    df_output["DATE"] = pd.to_datetime(df_output["DATE"])

    df_result = _merge_compdat_and_connstatus(df_compdat, df_connstatus)
    pd.testing.assert_frame_equal(df_result, df_output, check_like=True)


CASES = [
    # Simple case. Two layers in the same zone. Only the open one will be aggregated and
    # the resulting KH is therefore 1.
    pytest.param(
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "OP/SH", "KH", "ZONE"],
            data=[
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 1, "OPEN", 1, "Z1"],
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 2, "SHUT", 1, "Z1"],
            ],
        ),
        pd.DataFrame(
            columns=["DATE", "WELL", "OP/SH", "KH", "ZONE"],
            data=[[datetime(year=2000, month=1, day=1), "OP1", "OPEN", 1, "Z1"]],
        ),
        id="Simple case",
    ),
    # Case with multiple dates. KH is 0 in OP2 because is it SHUT in all layers.
    pytest.param(
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "OP/SH", "KH", "ZONE"],
            data=[
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 1, "OPEN", 1, "Z1"],
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 2, "SHUT", 1, "Z1"],
                [datetime(year=2000, month=2, day=1), "OP1", 1, 1, 1, "SHUT", 1, "Z1"],
                [datetime(year=2000, month=2, day=1), "OP1", 1, 1, 2, "SHUT", 1, "Z1"],
            ],
        ),
        pd.DataFrame(
            columns=["DATE", "WELL", "OP/SH", "KH", "ZONE"],
            data=[
                [datetime(year=2000, month=1, day=1), "OP1", "OPEN", 1, "Z1"],
                [datetime(year=2000, month=2, day=1), "OP1", "SHUT", 0, "Z1"],
            ],
        ),
        id="Multiple dates",
    ),
    # Case with multiple wells and zones.
    pytest.param(
        pd.DataFrame(
            columns=["DATE", "WELL", "I", "J", "K1", "OP/SH", "KH", "ZONE"],
            data=[
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 1, "OPEN", 1, "Z1"],
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 2, "OPEN", 1, "Z1"],
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 3, "OPEN", 1, "Z2"],
                [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 4, "OPEN", 1, "Z3"],
                [datetime(year=2000, month=1, day=1), "OP2", 1, 1, 5, "OPEN", 1, "Z4"],
                [datetime(year=2000, month=1, day=1), "OP2", 1, 1, 6, "OPEN", 1, "Z4"],
                [datetime(year=2000, month=1, day=1), "OP2", 1, 1, 7, "OPEN", 1, "Z4"],
                [datetime(year=2000, month=1, day=1), "OP2", 1, 1, 8, "OPEN", 1, "Z5"],
            ],
        ),
        pd.DataFrame(
            columns=["DATE", "WELL", "OP/SH", "KH", "ZONE"],
            data=[
                [datetime(year=2000, month=1, day=1), "OP1", "OPEN", 2, "Z1"],
                [datetime(year=2000, month=1, day=1), "OP1", "OPEN", 1, "Z2"],
                [datetime(year=2000, month=1, day=1), "OP1", "OPEN", 1, "Z3"],
                [datetime(year=2000, month=1, day=1), "OP2", "OPEN", 3, "Z4"],
                [datetime(year=2000, month=1, day=1), "OP2", "OPEN", 1, "Z5"],
            ],
        ),
        id="Multiple wells and zones",
    ),
]


@pytest.mark.parametrize("compdat_df, wellcompletion_df", CASES)
def test_aggregate_layer_to_zone(compdat_df, wellcompletion_df):
    """Tests the _aggregate_layer_to_zone function in wellcompletionsdata"""
    pd.testing.assert_frame_equal(
        _aggregate_layer_to_zone(compdat_df), wellcompletion_df, check_like=True
    )


def test_excl_well_startswith():
    """Tests the _excl_well_startswith function in wellcompletiondata.
    Only the well that starts with R_ is filtered out.
    """
    input_df = pd.DataFrame(
        columns=["DATE", "WELL", "I", "J", "K1", "OP/SH", "KH", "ZONE"],
        data=[
            [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 1, "OPEN", 1, "Z1"],
            [datetime(year=2000, month=1, day=1), "R_OP1", 1, 1, 1, "OPEN", 1, "Z1"],
            [datetime(year=2000, month=1, day=1), "OP1R_", 1, 1, 1, "OPEN", 1, "Z1"],
        ],
    )
    expected_df = pd.DataFrame(
        columns=["DATE", "WELL", "I", "J", "K1", "OP/SH", "KH", "ZONE"],
        data=[
            [datetime(year=2000, month=1, day=1), "OP1", 1, 1, 1, "OPEN", 1, "Z1"],
            [datetime(year=2000, month=1, day=1), "OP1R_", 1, 1, 1, "OPEN", 1, "Z1"],
        ],
    )
    pd.testing.assert_frame_equal(
        _excl_well_startswith(input_df, "R_").reset_index(drop=True),
        expected_df,
        check_like=True,
    )
