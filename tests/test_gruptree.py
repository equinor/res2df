"""Test module for nnc2df"""

from pathlib import Path

import pytest
import pandas as pd

from ecl2df import gruptree, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_gruptree2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
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


def test_grupnet_rst_docs(tmpdir):
    """Provide the input and output for the examples in the RST documentation"""
    tmpdir.chdir()
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


def test_emptytree_commandlinetool(tmpdir, mocker, caplog):
    tmpdir.chdir()
    Path("EMPTY.DATA").write_text("")
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", "--prettyprint", "EMPTY.DATA"])
    ecl2csv.main()
    assert "No tree data to prettyprint" in caplog.text


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


def test_main(tmpdir, mocker):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join("gruptree.csv")
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", DATAFILE, "-o", str(tmpcsvfile)])
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty


def test_prettyprint(mocker, capsys):
    """Test pretty printing via command line interface"""
    mocker.patch("sys.argv", ["ecl2csv", "gruptree", DATAFILE, "--prettyprint"])
    ecl2csv.main()
    stdout = capsys.readouterr().out.strip()
    print(stdout)
    assert (
        """
Date: 2000-01-01
FIELD
├── OP
└── WI


Date: 2000-02-01
FIELD
├── OP
│   ├── OP_1
│   ├── OP_2
│   └── OP_3
└── WI
    └── WI_1


Date: 2000-06-01
FIELD
├── OP
│   ├── OP_1
│   ├── OP_2
│   └── OP_3
└── WI
    ├── WI_1
    └── WI_2


Date: 2001-01-01
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


def test_main_subparser(tmpdir, mocker):
    """Test command line interface"""
    tmpcsvfile = tmpdir.join("gruptree.csv")
    mocker.patch(
        "sys.argv", ["ecl2csv", "gruptree", "-v", DATAFILE, "-o", str(tmpcsvfile)]
    )
    ecl2csv.main()

    assert Path(tmpcsvfile).is_file()
    disk_df = pd.read_csv(str(tmpcsvfile))
    assert not disk_df.empty
