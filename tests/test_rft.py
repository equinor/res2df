"""Test module for rft"""
import datetime
import os
import random
from pathlib import Path

import pandas as pd
import pytest

from ecl2df import ecl2csv, rft
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")

# pylint: disable=protected-access


def test_rftrecords2df():
    """Test that we can construct a dataframe for navigating in RFT
    records"""
    rftrecs = rft._rftrecords2df(EclFiles(EIGHTCELLS).get_rftfile())
    assert len(rftrecs[rftrecs["recordname"] == "TIME"]) == len(
        rftrecs["timeindex"].unique()
    )
    assert set(rftrecs["recordtype"].unique()) == set(["REAL", "INTE", "CHAR"])
    assert rftrecs["timeindex"].dtype == int
    assert rftrecs["recordidx"].dtype == int

    # Test that we have a consecutive index in "recordidx"
    assert (rftrecs["recordidx"] == rftrecs.index).all()


def test_rftrecords_generator():
    """Test the generator that will iterate over an EclFile/RFTFile
    and provide one yield pr.  well pr. date"""
    for rftrecord in rft.rftrecords(EclFiles(EIGHTCELLS).get_rftfile()):
        assert isinstance(rftrecord, dict)
        assert "date" in rftrecord
        assert isinstance(rftrecord["date"], datetime.date)
        assert "wellmodel" in rftrecord
        assert "timeindex" in rftrecord
        assert "wellname" in rftrecord
        assert len(rftrecord["wellname"]) < 9  # E100
        assert rftrecord["wellmodel"] in ["STANDARD", "MULTISEG"]
        assert "headers" in rftrecord
        assert isinstance(rftrecord["headers"], pd.DataFrame)


def test_get_con_seg_data():
    """Get CON data. Later add more code here to defend the name"""
    rftfile = EclFiles(EIGHTCELLS).get_rftfile()

    # Test the first record, it is a CON type (not multisegment)
    rftrecord = next(rft.rftrecords(rftfile))
    con_data = rft.get_con_seg_data(rftrecord, rftfile, "CON")
    assert {"CONIPOS", "CONJPOS", "CONKPOS", "DEPTH", "PRESSURE", "SWAT"}.issubset(
        set(con_data.columns)
    )
    assert all(con_data["CONIDX"] == con_data.index + 1)

    with pytest.raises(ValueError):
        rft.get_con_seg_data(None, None, "FOO")


def test_minimal_well():
    """Test a dummy well dataset

    |    segidx 1

    """
    one_seg = pd.DataFrame(
        {"SEGIDX": [1], "SEGNXT": [None], "SEGBRNO": [1], "SEGPRES": [195.8]}
    )
    with pytest.raises(ValueError, match="Insufficient topology"):
        rft.process_seg_topology(one_seg.drop("SEGIDX", axis="columns"))

    m_one_seg = rft.process_seg_topology(one_seg)
    assert m_one_seg["LEAF"][0]
    assert len(m_one_seg) == 1
    assert rft.count_wellbranches(one_seg) == 1
    assert rft.split_seg_icd(one_seg)[1].empty

    con_data = pd.DataFrame({"CONSEGNO": [1], "PRESSURE": [200.1], "CONPRES": [196.0]})
    con_seg = rft.merge_icd_seg_conseg(con_data, m_one_seg)
    assert len(con_seg) == 1
    assert "CONSEGNO" in con_seg
    assert "SEGIDX" in con_seg
    con_seg = rft.add_extras(con_seg)
    assert "COMPLETION_DP" in con_seg
    assert con_seg["COMPLETION_DP"].values[0] == 196.0 - 195.8
    assert con_seg["DRAWDOWN"].values[0] == 200.1 - 196.0
    assert rft.seg2dicttree(m_one_seg) == {1: {}}
    print(rft.pretty_print_well(m_one_seg))


def test_minimal_branched_well():
    r"""
     |       segidx 1
    / \      segidx 2 and 3
    """
    two_branch = pd.DataFrame(
        {"SEGIDX": [1, 2, 3], "SEGNXT": [None, 1, 1], "SEGBRNO": [1, 1, 2]}
    )
    con_data = pd.DataFrame(
        {"CONSEGNO": [2, 3], "PRESSURE": [301, 302], "CONPRES": [291, 292]}
    )
    m_two_branch = rft.process_seg_topology(two_branch)
    assert len(m_two_branch) == 4  # One extra row for the junction segment
    assert sum(m_two_branch["LEAF"]) == 2
    assert rft.count_wellbranches(m_two_branch) == 2
    assert rft.split_seg_icd(two_branch)[1].empty
    con_seg = rft.merge_icd_seg_conseg(con_data, m_two_branch)

    # Junction segment has no reservoir connection and is not included
    # in the merge.
    assert len(con_seg) == 2

    assert rft.seg2dicttree(m_two_branch) == {1: {2: {}, 3: {}}}
    # Junction segment points to two upstream segments:
    assert set(
        m_two_branch[m_two_branch["SEGIDX"] == 1]["SEGIDX_upstream"].astype(int)
    ) == {2, 3}
    assert int(m_two_branch.loc[0, "SEGIDX_upstream"]) == 2
    assert int(m_two_branch.loc[1, "SEGIDX_upstream"]) == 3


def test_single_branch_icd():
    """
    Test that we are able to untangle segment dataframes with ICDs
    modelled as individual brances.
    """

    # Single branch well, one mother segment, two connections,
    # one icd to each connection:

    #     |   segidx 1
    #     | - *  segidx 2 and 4, and reservoir
    #     | - *  segidx 3 and 5, and reservoir

    # legend: | = tubing
    #         - = icd
    #         * = reservoir connection
    wellseg = pd.DataFrame(
        {
            "SEGIDX": [1, 2, 3, 4, 5],
            "SEGNXT": [None, 1, 2, 2, 3],
            "SEGBRNO": [1, 1, 1, 2, 3],
        }
    )
    con_data = pd.DataFrame(
        {"CONSEGNO": [4, 5], "PRESSURE": [301, 302], "CONPRES": [291, 292]}
    )
    (seg_data, icd_data) = rft.split_seg_icd(wellseg)
    print(rft.seg2dicttree(wellseg))
    print(rft.pretty_print_well(wellseg))
    assert rft.count_wellbranches(seg_data) == 1

    assert len(icd_data) == 2
    assert all(icd_data.columns.str.startswith("ICD"))
    assert all(icd_data["ICD_SEGIDX"].values == [4, 5])
    assert all(icd_data["ICD_SEGBRNO"].values == [2, 3])
    assert all(icd_data["ICD_SEGBRNO_upstream"].values == [0, 0])

    con_seg = rft.merge_icd_seg_conseg(con_data, seg_data, icd_data)
    assert len(con_seg) == 2
    con_seg = rft.add_extras(con_seg)
    assert all(con_seg["DRAWDOWN"].values == [10, 10])


def test_single_branch_partly_icd():
    r"""
    Test that we are able to untangle segment dataframes with ICDs
    modelled as individual branches, but not on all reservoir connections

    Single branch well, one mother segment, two connections,
    one icd to one connection:

         |   segidx 1
         | - *  segidx 2 and 4 (icd), and reservoir
         | *  segidx 3, and reservoir

    legend: | = tubing
            - = icd
            * = reservoir connection


    This is the same layout as
       |  segidx 1
       |  segidx 2
      / \  segidx 3 and 4
     *   *
    which is a two-branch well. It is not possible to
    separate these two based on topology. Current code interprets
    the topology as the latter case.
    The ambiguity arises due to the assumption that ICD segments
    are on their on branches with only one segment. In real modelled
    wells, this assumption will be valid, as the tubing segments will
    consist of more segments than 1 (except corner cases)
    (check the LONELYSEG segment toplogy metadata column which
    is used in determining whether a segment is ICD or not)

    """
    wellseg = pd.DataFrame(
        {"SEGIDX": [1, 2, 3, 4], "SEGNXT": [None, 1, 2, 2], "SEGBRNO": [1, 1, 1, 2]}
    )
    con_data = pd.DataFrame(
        {"CONSEGNO": [4, 3], "PRESSURE": [301, 302], "CONPRES": [291, 292]}
    )
    (seg_data, icd_data) = rft.split_seg_icd(wellseg)
    print(rft.seg2dicttree(wellseg))
    print(rft.pretty_print_well(wellseg))
    assert rft.count_wellbranches(seg_data) == 2

    assert len(icd_data) == 0

    con_seg = rft.merge_icd_seg_conseg(con_data, seg_data, icd_data)
    assert len(con_seg) == 2
    con_seg = rft.add_extras(con_seg)
    assert all(con_seg["DRAWDOWN"].values == [10, 10])


def test_branched_icd_well():
    r"""Simplest possible branched well with ICD segments

         |          segidx 1
    * - / \ - *     segidx 2 and 3
    """
    wellseg = pd.DataFrame(
        {
            "SEGIDX": [1, 2, 3, 4, 5],
            "SEGNXT": [None, 1, 1, 2, 3],
            "SEGBRNO": [1, 1, 2, 3, 4],
        }
    )
    con_data = pd.DataFrame(
        {"CONSEGNO": [4, 5], "PRESSURE": [301, 302], "CONPRES": [291, 292]}
    )
    (seg_data, icd_data) = rft.split_seg_icd(wellseg)
    print(rft.seg2dicttree(wellseg))
    print(rft.pretty_print_well(wellseg))

    assert len(icd_data) == 2
    assert all(icd_data.columns.str.startswith("ICD"))
    assert all(icd_data["ICD_SEGIDX"].values == [4, 5])
    assert all(icd_data["ICD_SEGBRNO"].values == [3, 4])
    assert all(icd_data["ICD_SEGBRNO_upstream"].values == [0, 0])

    print(seg_data)
    assert rft.count_wellbranches(seg_data) == 2

    con_seg = rft.merge_icd_seg_conseg(con_data, seg_data, icd_data)
    print(con_seg)
    assert len(con_seg) == 2
    con_seg = rft.add_extras(con_seg)
    assert all(con_seg["DRAWDOWN"].values == [10, 10])


def test_longer_branched_icd_well():
    r"""Test a well with two connections on each of two laterals,
    with an ICD segment for each connection

           |          segidx 1
      * - / \ - *     segidx 4 and 2 (lateral1) and 6 and 8
      * - | | - *     segidx 5 and 3 (lateral1) and 7 and 9

    """
    wellseg = {
        "SEGIDX": [1] + [2, 3, 4, 5] + [6, 7, 8, 9],
        "SEGNXT": [None] + [1, 2, 2, 3] + [1, 6, 6, 7],
        "SEGBRNO": [1] + [1, 1, 3, 4] + [2, 2, 5, 6],
    }

    # Shuffle the segment list randomly, that should not matter:
    shuffled = list(range(9))
    random.shuffle(shuffled)
    print(shuffled)
    wellseg = pd.DataFrame(
        {segname: [wellseg[segname][idx] for idx in shuffled] for segname in wellseg}
    )

    con_data = pd.DataFrame(
        {
            "CONSEGNO": [4, 5, 8, 9],
            "PRESSURE": [301, 302, 401, 402],
            "CONPRES": [291, 292, 392, 393],
        }
    )
    seg_data = rft.process_seg_topology(wellseg)
    assert sum(seg_data["LONELYSEG"]) == 4
    assert sum(seg_data["LEAF"]) == 4
    assert sum(seg_data["JUNCTION"]) == 6  # 1, 2 and 6 counted twice
    assert sum(seg_data["LEAF"]) == 4
    (seg_data, icd_data) = rft.split_seg_icd(wellseg)
    print(rft.seg2dicttree(wellseg))
    print(rft.pretty_print_well(wellseg))

    assert len(icd_data) == 4
    assert all(icd_data.columns.str.startswith("ICD"))
    assert set(icd_data["ICD_SEGIDX"].values) == {4, 5, 8, 9}
    assert set(icd_data["ICD_SEGBRNO"].values) == {3, 4, 5, 6}
    assert all(icd_data["ICD_SEGBRNO_upstream"].values == [0, 0, 0, 0])

    print(seg_data)
    assert rft.count_wellbranches(seg_data) == 2

    con_seg = rft.merge_icd_seg_conseg(con_data, seg_data, icd_data)
    print(con_seg)
    assert len(con_seg) == 4
    con_seg = rft.add_extras(con_seg)
    assert all(con_seg["DRAWDOWN"].values == [10, 10, 9, 9])


def test_longer_branched_partly_icd_well():
    r"""Test a well with two connections on each of two laterals,
    with an ICD segment for each connection only on the first lateral

           |          segidx 1
      * - / \  *     segidx 4 and 2 (lateral1) and 6 and
      * - | |  *     segidx 5 and 3 (lateral1) and 7 and

    """
    wellseg = pd.DataFrame(
        {
            # [wellhead] + [lateral 1, tubing, then icd layer] + [lateral 2]
            "SEGIDX": [1] + [2, 3, 4, 5] + [6, 7],
            "SEGNXT": [None] + [1, 2, 2, 3] + [1, 6],
            "SEGBRNO": [1] + [1, 1, 3, 4] + [2, 2],
        }
    )

    con_data = pd.DataFrame(
        {
            "CONSEGNO": [4, 5, 6, 7],
            "PRESSURE": [301, 302, 401, 402],
            "CONPRES": [291, 292, 392, 393],
        }
    )
    (seg_data, icd_data) = rft.split_seg_icd(wellseg)
    print()
    print(seg_data)
    print(rft.seg2dicttree(wellseg))
    print(rft.pretty_print_well(wellseg))

    assert len(icd_data) == 2
    assert all(icd_data.columns.str.startswith("ICD"))
    assert set(icd_data["ICD_SEGIDX"].values) == {4, 5}
    assert set(icd_data["ICD_SEGBRNO"].values) == {3, 4}
    assert all(icd_data["ICD_SEGBRNO_upstream"].values == [0, 0])

    print(seg_data)
    assert rft.count_wellbranches(seg_data) == 2

    con_seg = rft.merge_icd_seg_conseg(con_data, seg_data, icd_data)
    print(con_seg)
    assert len(con_seg) == 4
    con_seg = rft.add_extras(con_seg)
    assert all(con_seg["DRAWDOWN"].values == [10, 10, 9, 9])


def test_seg2dicttree():
    assert rft.seg2dicttree(pd.DataFrame()) == {}
    with pytest.raises(ValueError):
        rft.seg2dicttree(pd.DataFrame({"SEGIDX": [1]}))

    with pytest.raises(KeyError, match="SEGBRNO"):
        rft.seg2dicttree(pd.DataFrame({"SEGIDX": [1], "SEGNXT": [None]}))

    # Simplest well:
    assert rft.seg2dicttree(
        pd.DataFrame({"SEGIDX": [1], "SEGNXT": [None], "SEGBRNO": [1]})
    ) == {1: {}}

    # Two branches:
    assert rft.seg2dicttree(
        pd.DataFrame(
            {"SEGIDX": [1, 2, 3], "SEGNXT": [None, 1, 1], "SEGBRNO": [1, 1, 2]}
        )
    ) == {1: {2: {}, 3: {}}}


@pytest.mark.parametrize(
    "dframe, inplace,  expected",
    [
        (pd.DataFrame(), True, pd.DataFrame()),
        (pd.DataFrame(), False, pd.DataFrame()),
        (
            pd.DataFrame([{"CONPRES": 30, "SEGPRES": 20}]),
            True,
            pd.DataFrame(
                [{"CONPRES": 30, "SEGPRES": 20, "COMPLETION_DP": 10, "DRAWDOWN": 0}]
            ),
        ),
        (
            pd.DataFrame([{"CONPRES": 30, "SEGPRES": 20}]),
            False,
            pd.DataFrame(
                [{"CONPRES": 30, "SEGPRES": 20, "COMPLETION_DP": 10, "DRAWDOWN": 0}]
            ),
        ),
        (
            pd.DataFrame([{"CONPRES": 30, "PRESSURE": 40}]),
            True,
            pd.DataFrame(
                [{"CONPRES": 30, "PRESSURE": 40, "DRAWDOWN": 10, "CONBPRES": 40}]
            ),
        ),
        (
            # Compute connection length
            pd.DataFrame([{"CONLENEN": 4, "CONLENST": 3}]),
            True,
            pd.DataFrame(
                [
                    {
                        "CONLENEN": 4,
                        "CONLENST": 3,
                        "CONMD": 3.5,
                        "CONLENTH": 1,
                        "DRAWDOWN": 0,
                    }
                ]
            ),
        ),
        (
            # Compute scaled rates (pr meter connection)
            pd.DataFrame([{"CONORAT": 400, "CONLENTH": 2}]),
            True,
            pd.DataFrame(
                [{"CONORAT": 400, "CONLENTH": 2, "CONORATS": 200.0, "DRAWDOWN": 0}]
            ),
        ),
        (
            pd.DataFrame([{"CONWRAT": 400, "CONLENTH": 2}]),
            True,
            pd.DataFrame(
                [{"CONWRAT": 400, "CONLENTH": 2, "CONWRATS": 200.0, "DRAWDOWN": 0}]
            ),
        ),
        (
            pd.DataFrame([{"CONGRAT": 400, "CONLENTH": 2}]),
            True,
            pd.DataFrame(
                [{"CONGRAT": 400, "CONLENTH": 2, "CONGRATS": 200.0, "DRAWDOWN": 0}]
            ),
        ),
    ],
)
def test_add_extras(dframe, inplace, expected):
    """Test addition of nice-to-have extras column."""
    original = dframe.copy()
    result = rft.add_extras(dframe, inplace)
    print(result)
    pd.testing.assert_frame_equal(result, expected, check_like=True)
    if inplace:
        pd.testing.assert_frame_equal(result, dframe)
    else:
        pd.testing.assert_frame_equal(dframe, original)


def test_rft2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(REEK)
    rftdf = rft.df(eclfiles)
    assert "ZONE" in rftdf
    assert "LEAF" not in rftdf  # Topology metadata should not be exported
    assert set(rftdf["WELLMODEL"]) == {"STANDARD"}
    assert set(rftdf["WELL"]) == {
        "OP_1",
        "OP_2",
        "OP_3",
        "OP_4",
        "OP_5",
        "WI_1",
        "WI_2",
        "WI_3",
    }
    assert not rftdf.empty
    assert len(rftdf) == 115
    # Each well has 14 or 15 reservoir connections (14 layers in grid)
    assert set(rftdf.groupby("WELL")["CONIDX"].count().values) == {14, 15}
    assert not rftdf.columns.empty


def test_main_subparsers(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / ".TMP-rft.csv"
    mocker.patch("sys.argv", ["ecl2csv", "rft", EIGHTCELLS, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty

    tmpcsvfile = tmp_path / ".TMP-rft2.csv"
    # Test with RFT file as argument:
    mocker.patch(
        "sys.argv",
        [
            "ecl2cvsv",
            "rft",
            "-v",
            REEK.replace(".DATA", ".RFT"),
            "-o",
            str(tmpcsvfile),
        ],
    )
    ecl2csv.main()
    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_main_debugmode(tmp_path, mocker):
    """Test debug mode"""
    os.chdir(tmp_path)
    mocker.patch(
        "sys.argv", ["ecl2csv", "rft", "--debug", EIGHTCELLS, "-o", "indebugmode.csv"]
    )
    ecl2csv.main()
    # Extra files emitted in debug mode:
    assert not pd.read_csv("con.csv").empty
    assert Path("seg.csv").exists()  # too simple example data, no segments.
    assert Path("icd.csv").exists()  # too simple example data, no ICD
