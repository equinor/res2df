"""Test module for ecl2df.common"""

import os
from pathlib import Path

import pandas as pd
import pytest

from ecl2df import common, eclfiles, equil

try:
    import opm  # noqa

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False


def test_opmkeywords():
    """Test that we have loaded some keyword metadata from json files on disk"""
    assert "WCONPROD" in common.OPMKEYWORDS
    assert common.OPMKEYWORDS["WCONPROD"]
    assert "name" in common.OPMKEYWORDS["WCONPROD"]
    assert "BHP" in [x["name"] for x in common.OPMKEYWORDS["WCONPROD"]["items"]]

    # This file should not be parsed..
    assert "README" not in common.OPMKEYWORDS


def test_stack_on_colname():
    """Test that we can stack column with an implicit double level
    in the column names indicated by a separator string"""

    dframe = pd.DataFrame(
        columns=["EQLNUM", "STATIC", "OWC@2000-01-01", "OWC@2020-01-01"],
        data=[[1, 1.2, 2000, 1900], [2, 1.3, 2100, 2050]],
    )
    orig_dframe = dframe.copy()
    common.stack_on_colnames(dframe, inplace=False)
    pd.testing.assert_frame_equal(dframe, orig_dframe)

    stacked = common.stack_on_colnames(dframe)
    assert not dframe.equals(orig_dframe)  # It was modifid in the process
    assert "DATE" in stacked
    assert "OWC" in stacked
    assert len(stacked.columns) == 4
    assert len(stacked["DATE"].unique()) == 2
    assert len(stacked) == 4
    assert not stacked.isnull().sum().sum()

    dframe = pd.DataFrame(
        columns=[
            "EQLNUM",
            "STATIC",
            "OWC@2000-01-01",
            "OWC@2020-01-01",
            "GOC@2000-01-01",
            "GOC@2020-01-01",
        ],
        data=[[1, 1.2, 2000, 1900, 1800, 1700], [2, 1.3, 2100, 2050, 2000, 1950]],
    )
    stacked = common.stack_on_colnames(dframe)
    assert "DATE" in stacked
    assert "OWC" in stacked
    assert "GOC" in stacked
    assert len(stacked.columns) == 5
    assert len(stacked["DATE"].unique()) == 2
    assert len(stacked) == 4
    assert not stacked.isnull().sum().sum()

    dframe = pd.DataFrame(
        columns=["OWC@2000-01-01", "OWC@2020-01-01"], data=[[2000, 1900], [2100, 2050]]
    )
    stacked = common.stack_on_colnames(dframe)
    assert "DATE" in stacked
    assert "OWC" in stacked
    assert len(stacked.columns) == 2
    assert len(stacked["DATE"].unique()) == 2
    assert len(stacked) == 4
    assert not stacked.isnull().sum().sum()

    dframe = pd.DataFrame(columns=["EQLNUM", "STATIC"], data=[[1, 1.2], [2, 1.3]])
    stacked = common.stack_on_colnames(dframe)
    assert "DATE" not in stacked
    assert "OWC" not in stacked
    assert "EQLNUM" in stacked
    assert "STATIC" in stacked
    assert len(stacked.columns) == 2
    assert len(stacked) == 2
    assert not stacked.isnull().sum().sum()


def test_write_dframe_file(tmp_path):
    """Test that we can write dataframes to files."""
    os.chdir(tmp_path)
    dframe = pd.DataFrame([{"foo": "bar"}])
    common.write_dframe_stdout_file(dframe, "foo.csv")
    pd.testing.assert_frame_equal(pd.read_csv("foo.csv"), dframe)


def test_write_dframe_stdout(capsys):
    """Test that we can write dataframes to stdout."""
    dframe = pd.DataFrame([{"foo": "bar"}])
    common.write_dframe_stdout_file(dframe, common.MAGIC_STDOUT)
    assert "foo\nbar" in capsys.readouterr().out


def test_write_inc_file(tmp_path):
    """Test that we can write include files to files."""
    os.chdir(tmp_path)
    string = "PORO\n0\n/"
    common.write_inc_stdout_file(string, "poro.inc")
    assert Path("poro.inc").read_text() == string


def test_write_inc_stdout(capsys):
    """Test that we can write include files to stdout."""
    string = "PORO\n0\n/"
    common.write_inc_stdout_file(string, common.MAGIC_STDOUT)
    assert string in capsys.readouterr().out


def test_parse_opmio_deckrecord():
    """Test common properties of the general parse_opmio_deckrecord.

    This function is also indirectly tested in each different
    submodule"""
    with pytest.raises(ValueError, match="Keyword FOOBAR not supported"):
        common.parse_opmio_deckrecord(None, "FOOBAR")


@pytest.mark.skipif(not HAVE_OPM, reason="OPM is not installed")
@pytest.mark.parametrize(
    "wanted, deckstr, supported, expected",
    [
        ("PORO", "PORO\n/", ["PORO"], ["PORO"]),
        (["PORO"], "PORO\n/", ["PORO"], ["PORO"]),
        ("PORO", "PORO\n/", [], []),
        ("PERMX", "PORO\n/", ["PORO"], []),
        ("PERMX", "PERMX\n/", ["PORO"], []),
        ("PERMX", "PORO\n/", ["PERMX"], []),
    ],
)
def test_handle_wanted_keywords(wanted, deckstr, supported, expected):
    """Test that we can handle list of wanted, supported and available keywords."""
    deck = eclfiles.EclFiles.str2deck(deckstr)
    assert common.handle_wanted_keywords(wanted, deck, supported) == expected


def df2ecl_equil(dframe, comment: str = None):
    """Wrapper function to be able to test df2ecl

    (it asks for a function in the calling module)"""
    return equil.df2ecl_equil(dframe, comment)


def test_df2ecl():
    """Test general properties of df2ecl.

    This function is mainly tested in each submodule."""
    dframe = pd.DataFrame(
        [
            {
                "Z": 2469.0,
                "PRESSURE": 382.4,
                "OWC": 100.0,
                "PCOWC": 0.0,
                "GOC": 0.0,
                "EQLNUM": 1,
                "KEYWORD": "EQUIL",
            }
        ]
    )
    with pytest.raises(AssertionError):
        # supported keywords are not supplied
        common.df2ecl(dframe)
    with pytest.raises(AssertionError):
        common.df2ecl(dframe, supported=None)

    with pytest.raises(ValueError, match="KEYWORD must be in the dataframe"):
        common.df2ecl(
            dframe.drop("KEYWORD", axis=1), keywords=["EQUIL"], supported=["EQUIL"]
        )

    string = common.df2ecl(dframe, supported=["EQUIL"])
    # The next calls differ only in timestamp:
    assert len(string) == len(
        common.df2ecl(dframe, keywords="EQUIL", supported=["EQUIL"])
    )
    assert len(string) == len(
        common.df2ecl(dframe, keywords=["EQUIL"], supported=["EQUIL"])
    )
    assert "EQUIL\n" in string
    assert "2469" in string
    assert "-- Output file printed by tests.test_common" in string

    assert "" == common.df2ecl(dframe, supported=["PORO"])

    assert "EQUIL\n-- foobar" in common.df2ecl(
        dframe, comments={"EQUIL": "foobar"}, supported=["EQUIL"]
    )
    assert "\n\n-- masterfoobar\nEQUIL" in common.df2ecl(
        dframe, comments={"master": "masterfoobar"}, supported=["EQUIL"]
    )

    tworows = pd.concat([dframe, dframe])
    tworows["EQLNUM"] = [3, 1]
    tworows["PRESSURE"] = [3456, 1234]
    with pytest.raises(ValueError):
        common.df2ecl(tworows, supported=["EQUIL"], consecutive="EQLNUM")
    # This would be a bug if client code did this, because the wrong
    # consecutive column is set:
    assert "3456" in common.df2ecl(tworows, supported=["EQUIL"], consecutive="PVTNUM")
    tworows["EQLNUM"] = [1, 3]
    with pytest.raises(ValueError):
        common.df2ecl(tworows, supported=["EQUIL"], consecutive="EQLNUM")
    tworows["EQLNUM"] = [2, 1]
    # Passes because the frame is sorted on EQLNUM:
    string = common.df2ecl(tworows, supported=["EQUIL"], consecutive="EQLNUM")
    assert "EQUIL" in string
    assert string.find("3456") > string.find("1234")


def test_eclcompress():
    """Test that we can compress string using Eclipse style
    run-length encoding"""
    assert common.runlength_eclcompress("") == ""
    assert common.runlength_eclcompress(" ") == ""
    assert common.runlength_eclcompress("1 2") == "1  2"
    assert common.runlength_eclcompress("1 2", sep=" ") == "1 2"
    assert common.runlength_eclcompress("1 2", sep="   ") == "1   2"
    assert common.runlength_eclcompress("1") == "1"
    assert common.runlength_eclcompress("1 1") == "2*1"
    assert common.runlength_eclcompress("1 1 1") == "3*1"
    assert common.runlength_eclcompress("1     1 1") == "3*1"
    assert common.runlength_eclcompress("1  \n  1 1 2") == "3*1  2"


@pytest.mark.parametrize(
    "template, wells, output",
    [
        ("OP*", ["OP1", "OP2", "WI"], ["OP1", "OP2"]),
        ("B*H", ["B_1H", "BH", "B_23H", "WI"], ["B_1H", "BH", "B_23H"]),
        ("B_1H*", ["B_1H", "B_1HT2", "OB_1H"], ["B_1H", "B_1HT2"]),
        ("\\*P1", ["OP1", "WI"], ["OP1"]),
        ("B_?H", ["B_1H", "B_12H"], ["B_1H"]),
        ("\\????", ["B_1H", "D_2H", "OP1"], ["B_1H", "D_2H"]),
        pytest.param(
            "*P1",
            ["OP1"],
            None,
            marks=pytest.mark.xfail(
                raises=ValueError,
                match="Well template not allowed to start with a wildcard character",
            ),
        ),
        pytest.param(
            "????",
            ["B_1H"],
            None,
            marks=pytest.mark.xfail(
                raises=ValueError,
                match="Well template not allowed to start with a wildcard character",
            ),
        ),
    ],
)
def test_well_matching_template(template, wells, output):
    "Test that get_wells_matching_template is working as intended."
    assert common.get_wells_matching_template(template, wells) == output
