"""Test module for nnc2df"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ecl2df import ecl2csv, gruptree
from ecl2df.eclfiles import EclFiles

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed, nothing relevant in here then",
        allow_module_level=True,
    )

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")
# EIGTHCELLS is to be used in test_main_subparser when #356 is solved:
EIGHTCELLS = str(TESTDIR / "data/eightcells/EIGHTCELLS.DATA")


def test_eightcells_dataset():
    """Test Eightcells dataset"""
    eclfiles = EclFiles(EIGHTCELLS)
    gruptree_df = gruptree.df(eclfiles.get_ecldeck())

    expected_dframe = pd.DataFrame(
        [
            ["2000-01-01", "FIELD", "GRUPTREE", np.nan],
            ["2000-01-01", "OP1", "WELSPECS", "OPS"],
            ["2000-01-01", "OPS", "GRUPTREE", "FIELD"],
        ],
        columns=["DATE", "CHILD", "KEYWORD", "PARENT"],
    )
    expected_dframe["DATE"] = pd.to_datetime(expected_dframe["DATE"])
    pd.testing.assert_frame_equal(gruptree_df, expected_dframe, check_dtype=False)


def test_gruptree2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(REEK)
    grupdf = gruptree.df(eclfiles.get_ecldeck())

    assert not grupdf.empty
    assert len(grupdf["DATE"].unique()) == 5
    assert len(grupdf["CHILD"].unique()) == 11
    assert len(grupdf["PARENT"].dropna().unique()) == 3
    assert set(grupdf["KEYWORD"].unique()) == set(["GRUPTREE", "WELSPECS"])

    grupdfnowells = gruptree.df(eclfiles.get_ecldeck(), welspecs=False)

    assert len(grupdfnowells["KEYWORD"].unique()) == 1
    assert grupdf["PARENT"].dropna().unique()[0] == "FIELD"
    assert grupdf["KEYWORD"].unique()[0] == "GRUPTREE"


def test_str2df():
    """Test when we send in a string directly"""
    schstr = """
GRUPTREE
 'OPWEST' 'OP' /
 'OP' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

WELSPECS
 'OP1' 'OPWEST' 41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    assert grupdf.dropna().empty  # the DATE is empty

    # This is only available if GRUPNET is also there
    assert "TERMINAL_PRESSURE" not in grupdf

    withstart = gruptree.df(deck, startdate="2019-01-01")
    assert not withstart.dropna().empty
    assert len(withstart) == 6


def test_grupnet_rst_docs(tmp_path):
    """Provide the input and output for the examples in the RST documentation"""
    os.chdir(tmp_path)
    schstr = """
START
 01 'JAN' 2000 /

SCHEDULE

GRUPTREE
 'OPEAST' 'OP' /
 'OPWEST' 'OP' /
 'INJEAST' 'WI' /
 'OP' 'FIELD' /
 'WI' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

GRUPNET
  'FIELD' 90 /
  'OPWEST' 100 /
/

WELSPECS
 'OP1'  'OPWEST'  41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
 'OP2'  'OPEAST'  43 122 1776.01 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
 'INJ1' 'INJEAST' 33 115 1960.21 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    grupdf[["DATE", "CHILD", "PARENT", "KEYWORD"]].to_csv("gruptree.csv", index=False)
    grupdf.to_csv("gruptreenet.csv", index=False)
    grup_dict = gruptree.edge_dataframe2dict(grupdf)
    print("Copy and paste into RST files:")
    print(str(gruptree.tree_from_dict(grup_dict[0])))

    assert (
        str(gruptree.tree_from_dict(grup_dict[0])).strip()
        == """
NORTHSEA
└── AREA
    └── FIELD
        ├── OP
        │   ├── OPEAST
        │   │   └── OP2
        │   └── OPWEST
        │       └── OP1
        └── WI
            └── INJEAST
                └── INJ1
    """.strip()
    )


def test_grupnetdf():
    """Test making a dataframe from a GRUPTREE string"""
    schstr = """
GRUPTREE
 'OPWEST' 'OP' /
 'OP' 'FIELD' /
 'WI' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

GRUPNET
  'FIELD' 90 /
  'OPWEST' 100 /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck, startdate="2000-01-01")
    print(grupdf)
    assert "TERMINAL_PRESSURE" in grupdf
    assert 90 in grupdf["TERMINAL_PRESSURE"].values
    assert 100 in grupdf["TERMINAL_PRESSURE"].values


@pytest.mark.parametrize(
    "dicttree, expected_str",
    [
        ({}, ""),
        ({"foo": {}}, "foo"),
        ({"foo": {"bar": {}}}, "foo\n└── bar"),
        ({"foo": {"bar": {}, "com": {}}}, "foo\n├── bar\n└── com"),
        # Test sorting:
        ({"foo": {"com": {}, "bar": {}}}, "foo\n├── bar\n└── com"),
        # Two levels:
        (
            {"foo": {"bar": {}, "com": {"fjooo": {}}}},
            """
foo
├── bar
└── com
    └── fjooo""",
        ),
        # Integers as node names:
        ({1: {2: {}}}, "1\n└── 2"),
        # More complex structure:
        # Note: Node names cannot be duplicated, even on
        # unique branches:
        (
            {
                "foo": {
                    "bar": {},
                    "com": {"fjooo": {}},
                    "bart": {},
                    "comt": {"fjooot": {}},
                }
            },
            """
foo
├── bar
├── bart
├── com
│   └── fjooo
└── comt
    └── fjooot
            """,
        ),
    ],
)
def test_tree_from_dict(dicttree, expected_str):
    assert str(gruptree.tree_from_dict(dicttree)).strip() == expected_str.strip()


def test_dict2treelib_deprecated():
    """dict2treelib is deprecated and replaced by tree_from_dict()"""
    with pytest.warns(FutureWarning):
        gruptree.dict2treelib("foo", {"bar": {}})


@pytest.mark.parametrize(
    "schstr, expected_dframe, expected_tree",
    [
        (
            """
GRUPTREE
 'OP' 'FIELD'/
/

GRUPNET
  'FIELD' 90 /
  'OP' 100 /
/
        """,
            pd.DataFrame(
                [
                    {"CHILD": "FIELD", "PARENT": None, "TERMINAL_PRESSURE": 90},
                    {"CHILD": "OP", "PARENT": "FIELD", "TERMINAL_PRESSURE": 100},
                ]
            ),
            """
FIELD
└── OP
""",
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """
GRUPTREE
 'OP' 'FIELDA'/
/

GRUPNET
  'FIELDA' 90 /
  'OP' 100 /
  'FIELDB' 80 /   -- This is ignored when it is not in the GRUPTREE!
/
        """,
            pd.DataFrame(
                [
                    {"CHILD": "FIELDA", "PARENT": None, "TERMINAL_PRESSURE": 90},
                    {"CHILD": "OP", "PARENT": "FIELDA", "TERMINAL_PRESSURE": 100},
                ]
            ),
            """
FIELDA
└── OP
""",
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            """
GRUPTREE
 'OP' 'FIELDA'/
 'OPX' 'FIELDB' /
/

GRUPNET
  'FIELDA' 90 /
  'OP' 100 /
  'FIELDB' 80 /
/
        """,
            pd.DataFrame(
                [
                    {"CHILD": "FIELDB", "PARENT": None, "TERMINAL_PRESSURE": 80},
                    {"CHILD": "FIELDA", "PARENT": None, "TERMINAL_PRESSURE": 90},
                    {"CHILD": "OP", "PARENT": "FIELDA", "TERMINAL_PRESSURE": 100},
                    {"CHILD": "OPX", "PARENT": "FIELDB", "TERMINAL_PRESSURE": None},
                ]
            ),
            """
FIELDA
└── OP
FIELDB
└── OPX
""",
        )
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    ],
)
def test_grupnetroot(schstr, expected_dframe, expected_tree):
    """Test that terminal pressure of the tree root can be
    included in the dataframe (with an empty parent)"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck, startdate="2000-01-01")
    non_default_columns = ["CHILD", "PARENT", "TERMINAL_PRESSURE"]
    pd.testing.assert_frame_equal(
        grupdf[non_default_columns]
        .sort_values(["CHILD", "PARENT"])
        .reset_index(drop=True),
        expected_dframe.sort_values(["CHILD", "PARENT"]).reset_index(drop=True),
        check_dtype=False,
    )
    treelist = gruptree.edge_dataframe2dict(grupdf)
    # Merge strings for all trees (if multiple roots)
    strtrees = [str(gruptree.tree_from_dict(tree)) for tree in treelist]
    strtrees.sort()  # Avoid flaky test due to sorting
    treelibtree = "".join(strtrees)
    assert treelibtree.strip() == expected_tree.strip()


def test_multiple_roots():
    """Test edge_dataframe2dict with multiple roots"""
    answer = [
        {"FIELDA": {"PLATA": {}}},
        {"FIELDB": {"PLATB": {}}},
    ]
    edges = pd.DataFrame(
        [
            {"CHILD": "FIELDA", "PARENT": None},
            {"CHILD": "FIELDB", "PARENT": None},
            {"CHILD": "PLATA", "PARENT": "FIELDA"},
            {"CHILD": "PLATB", "PARENT": "FIELDB"},
        ]
    )
    assert gruptree.edge_dataframe2dict(edges) == answer

    # Same result if the dummy rows for the roots are omitted:
    edges_noroots = pd.DataFrame(
        [
            {"CHILD": "PLATA", "PARENT": "FIELDA"},
            {"CHILD": "PLATB", "PARENT": "FIELDB"},
        ]
    )
    assert gruptree.edge_dataframe2dict(edges_noroots) == answer

    # And order does not matter, should be sorted on root node label:
    edges_noroots = pd.DataFrame(
        [
            {"CHILD": "PLATB", "PARENT": "FIELDB"},
            {"CHILD": "PLATA", "PARENT": "FIELDA"},
        ]
    )
    assert gruptree.edge_dataframe2dict(edges_noroots) == answer

    # The function tree_from_dict should be called with one tree at a time:
    with pytest.raises(ValueError, match="single tree"):
        gruptree.tree_from_dict({"foo": 1, "bar": 2})


@pytest.mark.parametrize(
    "dframe, expected",
    [
        (pd.DataFrame(), [{}]),
        pytest.param(
            pd.DataFrame([{"FOO": "BAR"}]),
            [{}],
            marks=pytest.mark.xfail(raises=KeyError),
            # "PARENT" is required.
        ),
        pytest.param(
            pd.DataFrame([{"PARENT": "A"}]),
            [{}],
            marks=pytest.mark.xfail(raises=KeyError)
            # "CHILD" is also required
        ),
        (pd.DataFrame([{"PARENT": "A", "CHILD": "B"}]), [{"A": {"B": {}}}]),
        (
            pd.DataFrame(
                [{"PARENT": "A", "CHILD": "B"}, {"PARENT": "B", "CHILD": "C"}]
            ),
            [{"A": {"B": {"C": {}}}}],
        ),
        (
            # DATE is not used
            pd.DataFrame([{"PARENT": "A", "CHILD": "B", "DATE": "2000-01-01"}]),
            [{"A": {"B": {}}}],
        ),
        pytest.param(
            # DATE is not used, but will be checked that it is the same:
            pd.DataFrame(
                [
                    {"PARENT": "A", "CHILD": "B", "DATE": "2000-01-01"},
                    {"PARENT": "A", "CHILD": "B", "DATE": "2040-01-01"},
                ]
            ),
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ],
)
def test_edge_dataframe2dict(dframe, expected):
    assert gruptree.edge_dataframe2dict(dframe) == expected


def test_emptytree_strdeck():
    """Test empty schedule sections. Don't want to crash"""
    schstr = ""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    assert grupdf.empty
    gruptreedict = gruptree.edge_dataframe2dict(grupdf)
    assert not gruptreedict[0]

    treelibtree = gruptree.tree_from_dict(gruptreedict[0])
    # Returning an empty string and not a treelib.Tree() is
    # a workaround for a limitation in treelib.
    assert treelibtree == ""


def test_emptytree_commandlinetool(tmp_path, mocker, caplog):
    os.chdir(tmp_path)
    Path("EMPTY.DATA").write_text("")
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", "--prettyprint", "EMPTY.DATA"])
    ecl2csv.main()
    assert "No tree data to prettyprint" in caplog.text


def test_cli_nothing_to_do(mocker, capsys):
    """Test that the client says nothing to do when DATA is supplied, but no action."""
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", "EMPTY.DATA"])
    with pytest.raises(SystemExit):
        ecl2csv.main()
    assert "Nothing to do" in capsys.readouterr().out


def test_tstep():
    """Test that we can parse a deck using TSTEP for timestepping"""
    schstr = """
GRUPTREE
 'OPWEST' 'OP' /
 'OP' 'FIELD' /
 'FIELD' 'AREA' /
 'AREA' 'NORTHSEA' /
/

TSTEP
  1 /

WELSPECS
 'OP1' 'OPWEST' 41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
/

"""
    deck = EclFiles.str2deck(schstr)
    grupdf = gruptree.df(deck)
    assert len(grupdf["DATE"].unique()) == 2
    print(grupdf)


def test_main(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / "gruptree.csv"
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", REEK, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_prettyprint_commandline(mocker, capsys):
    """Test pretty printing via command line interface"""
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", REEK, "--prettyprint"])
    ecl2csv.main()
    stdout = capsys.readouterr().out.strip()
    print(stdout)
    assert (
        """
Date: 2000-01-01
GRUPTREE trees:
FIELD
├── OP
└── WI


Date: 2000-02-01
GRUPTREE trees:
FIELD
├── OP
│   ├── OP_1
│   ├── OP_2
│   └── OP_3
└── WI
    └── WI_1


Date: 2000-06-01
GRUPTREE trees:
FIELD
├── OP
│   ├── OP_1
│   ├── OP_2
│   └── OP_3
└── WI
    ├── WI_1
    └── WI_2


Date: 2001-01-01
GRUPTREE trees:
FIELD
├── OP
│   ├── OP_1
│   ├── OP_2
│   ├── OP_3
│   ├── OP_4
│   └── OP_5
└── WI
    ├── WI_1
    └── WI_2


Date: 2001-03-01
GRUPTREE trees:
FIELD
├── OP
│   ├── OP_1
│   ├── OP_2
│   ├── OP_3
│   ├── OP_4
│   └── OP_5
└── WI
    ├── WI_1
    ├── WI_2
    └── WI_3
""".strip()
        in stdout
    )


def test_main_subparser(tmp_path, mocker):
    """Test command line interface"""
    tmpcsvfile = tmp_path / "gruptree.csv"
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", "-v", REEK, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


@pytest.mark.parametrize(
    "schstr, expected_dframe, check_columns",
    [
        (
            # Changing BRANPROP
            """
DATES
  1 JAN 2000 /
/
GRUPTREE
 'TMPL_A' 'FIELD'/
/
BRANPROP
  'NODE_A'  'FIELD'  1 /
  'TMPL_A'  'NODE_A' 2 /
/
NODEPROP
  'FIELD'  20 /
  'TMPL_A'  2*  YES /
/
DATES
  1 FEB 2000 /
/
BRANPROP
  'NODE_B'  'FIELD'  3 /
  'TMPL_A'  'NODE_B' 4 /
/
        """,
            pd.DataFrame(
                [
                    ["2000-01-01", "FIELD", "GRUPTREE", np.nan, np.nan, np.nan],
                    ["2000-01-01", "TMPL_A", "GRUPTREE", "FIELD", np.nan, np.nan],
                    ["2000-01-01", "FIELD", "BRANPROP", np.nan, np.nan, 20],
                    ["2000-01-01", "NODE_A", "BRANPROP", "FIELD", 1, np.nan],
                    ["2000-01-01", "TMPL_A", "BRANPROP", "NODE_A", 2, np.nan],
                    ["2000-02-01", "FIELD", "BRANPROP", np.nan, np.nan, 20],
                    ["2000-02-01", "NODE_A", "BRANPROP", "FIELD", 1, np.nan],
                    ["2000-02-01", "NODE_B", "BRANPROP", "FIELD", 3, np.nan],
                    ["2000-02-01", "TMPL_A", "BRANPROP", "NODE_B", 4, np.nan],
                ],
                columns=[
                    "DATE",
                    "CHILD",
                    "KEYWORD",
                    "PARENT",
                    "VFP_TABLE",
                    "TERMINAL_PRESSURE",
                ],
            ),
            ["DATE", "CHILD", "KEYWORD", "PARENT", "VFP_TABLE", "TERMINAL_PRESSURE"],
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            # Changing NODEPROP
            """
DATES
  1 JAN 2000 /
/
GRUPTREE
 'TMPL_A' 'FIELD'/
/
BRANPROP
  'NODE_A'  'FIELD'  /
  'TMPL_A'  'NODE_A'  /
/
NODEPROP
  'FIELD'  20 /
  'TMPL_A'  2*  YES /
/
DATES
  1 FEB 2000 /
/
NODEPROP
  'FIELD'  22  1* YES /
/
        """,
            pd.DataFrame(
                [
                    ["2000-01-01", "FIELD", "GRUPTREE", np.nan, np.nan, np.nan],
                    ["2000-01-01", "TMPL_A", "GRUPTREE", "FIELD", np.nan, np.nan],
                    ["2000-01-01", "FIELD", "BRANPROP", np.nan, 20, "NO"],
                    ["2000-01-01", "NODE_A", "BRANPROP", "FIELD", np.nan, np.nan],
                    ["2000-01-01", "TMPL_A", "BRANPROP", "NODE_A", np.nan, "YES"],
                    ["2000-02-01", "FIELD", "BRANPROP", np.nan, 22, "YES"],
                    ["2000-02-01", "NODE_A", "BRANPROP", "FIELD", np.nan, np.nan],
                    ["2000-02-01", "TMPL_A", "BRANPROP", "NODE_A", np.nan, "YES"],
                ],
                columns=[
                    "DATE",
                    "CHILD",
                    "KEYWORD",
                    "PARENT",
                    "TERMINAL_PRESSURE",
                    "ADD_GAS_LIFT_GAS",
                ],
            ),
            [
                "DATE",
                "CHILD",
                "KEYWORD",
                "PARENT",
                "TERMINAL_PRESSURE",
                "ADD_GAS_LIFT_GAS",
            ],
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        (
            # WELSPECS
            """
DATES
  1 JAN 2000 /
/
GRUPTREE
 'TMPL_A' 'FIELD'/
/
BRANPROP
  'NODE_A'  'FIELD'  /
  'TMPL_A'  'NODE_A'  /
/
NODEPROP
  'FIELD'  20 /
  'TMPL_A'  2*  YES /
/
WELSPECS
  'WELL_1'  'TMPL_A' 1 1 1 OIL /
  'WELL_2'  'TMPL_B' 1 1 1 OIL /
/
DATES
  1 FEB 2000 /
/
NODEPROP
  'FIELD' 22 /
/
        """,
            # TMPL_B is not in any trees. The WELSPECS line is added
            # only when there is a new GRUPTREE tree and a GRUPTREE
            # entry is added connecting TMPL_B to the FIELD node.
            # TMPL_A is in both trees, but is not repeated at the date
            # where there are two trees
            pd.DataFrame(
                [
                    ["2000-01-01", "FIELD", "GRUPTREE", np.nan],
                    ["2000-01-01", "TMPL_A", "GRUPTREE", "FIELD"],
                    ["2000-01-01", "WELL_2", "WELSPECS", "TMPL_B"],
                    ["2000-01-01", "TMPL_B", "GRUPTREE", "FIELD"],
                    ["2000-01-01", "FIELD", "BRANPROP", np.nan],
                    ["2000-01-01", "NODE_A", "BRANPROP", "FIELD"],
                    ["2000-01-01", "TMPL_A", "BRANPROP", "NODE_A"],
                    ["2000-01-01", "WELL_1", "WELSPECS", "TMPL_A"],
                    ["2000-02-01", "FIELD", "BRANPROP", np.nan],
                    ["2000-02-01", "NODE_A", "BRANPROP", "FIELD"],
                    ["2000-02-01", "TMPL_A", "BRANPROP", "NODE_A"],
                    ["2000-02-01", "WELL_1", "WELSPECS", "TMPL_A"],
                ],
                columns=["DATE", "CHILD", "KEYWORD", "PARENT"],
            ),
            ["DATE", "CHILD", "KEYWORD", "PARENT"],
        ),
        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    ],
)
def test_branprop_nodeprop(schstr, expected_dframe, check_columns):
    """Testing that the gruptree dataframe works correctly
    when the schedule string contains BRANPROP and NODEPROP
    """
    deck = EclFiles.str2deck(schstr)
    dframe = gruptree.df(deck).reset_index()
    expected_dframe.DATE = pd.to_datetime(expected_dframe.DATE)
    pd.testing.assert_frame_equal(
        dframe[check_columns],
        expected_dframe[check_columns],
        check_dtype=False,
    )


def test_prettyprint(tmp_path, mocker, caplog):
    """ "Test prettyprinting with multiple dates and both
    GRUPTREE and BRANPROP trees"""
    schstr = """
DATES
  1 JAN 2000 /
/
GRUPTREE
 'TMPL_A' 'FIELD'/
/
BRANPROP
  'NODE_A'  'FIELD'  /
  'TMPL_A'  'NODE_A'  /
/
NODEPROP
  'FIELD'  20 /
  'TMPL_A'  2*  YES /
/
WELSPECS
  'WELL_1'  'TMPL_A' 1 1 1 OIL /
  'WELL_2'  'TMPL_B' 1 1 1 OIL /
/
DATES
  1 FEB 2000 /
/
NODEPROP
  'FIELD' 22 /
/
    """

    expected_prettyprint = """
Date: 2000-01-01
GRUPTREE trees:
FIELD
├── TMPL_A
│   └── WELL_1
└── TMPL_B
    └── WELL_2

BRANPROP trees:
FIELD
└── NODE_A
    └── TMPL_A
        └── WELL_1


Date: 2000-02-01
BRANPROP trees:
FIELD
└── NODE_A
    └── TMPL_A
        └── WELL_1


    """
    dframe = gruptree.df(EclFiles.str2deck(schstr))
    assert gruptree.prettyprint(dframe).strip() == expected_prettyprint.strip()
