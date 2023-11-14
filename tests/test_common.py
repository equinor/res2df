"""Test module for res2df.common"""

import datetime
import os
from pathlib import Path

import numpy as np
import packaging.version
import pandas as pd
import pytest

from res2df import common, equil, resdatafiles

try:
    # pylint: disable=unused-import
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
    assert Path("poro.inc").read_text(encoding="utf8") == string


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
    deck = resdatafiles.ResdataFiles.str2deck(deckstr)
    assert common.handle_wanted_keywords(wanted, deck, supported) == expected


def df2res_equil(dframe, comment: str = None):
    """Wrapper function to be able to test df2res

    (it asks for a function in the calling module)"""
    return equil.df2res_equil(dframe, comment)


def test_df2res():
    """Test general properties of df2res.

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
        common.df2res(dframe)
    with pytest.raises(AssertionError):
        common.df2res(dframe, supported=None)

    with pytest.raises(ValueError, match="KEYWORD must be in the dataframe"):
        common.df2res(
            dframe.drop("KEYWORD", axis=1), keywords=["EQUIL"], supported=["EQUIL"]
        )

    string = common.df2res(dframe, supported=["EQUIL"])
    # The next calls differ only in timestamp:
    assert len(string) == len(
        common.df2res(dframe, keywords="EQUIL", supported=["EQUIL"])
    )
    assert len(string) == len(
        common.df2res(dframe, keywords=["EQUIL"], supported=["EQUIL"])
    )
    assert "EQUIL\n" in string
    assert "2469" in string
    assert "-- Output file printed by tests.test_common" in string

    assert common.df2res(dframe, supported=["PORO"]) == ""

    assert "EQUIL\n-- foobar" in common.df2res(
        dframe, comments={"EQUIL": "foobar"}, supported=["EQUIL"]
    )
    assert "\n\n-- masterfoobar\nEQUIL" in common.df2res(
        dframe, comments={"master": "masterfoobar"}, supported=["EQUIL"]
    )

    tworows = pd.concat([dframe, dframe])
    tworows["EQLNUM"] = [3, 1]
    tworows["PRESSURE"] = [3456, 1234]
    with pytest.raises(ValueError):
        common.df2res(tworows, supported=["EQUIL"], consecutive="EQLNUM")
    # This would be a bug if client code did this, because the wrong
    # consecutive column is set:
    assert "3456" in common.df2res(tworows, supported=["EQUIL"], consecutive="PVTNUM")
    tworows["EQLNUM"] = [1, 3]
    with pytest.raises(ValueError):
        common.df2res(tworows, supported=["EQUIL"], consecutive="EQLNUM")
    tworows["EQLNUM"] = [2, 1]
    # Passes because the frame is sorted on EQLNUM:
    string = common.df2res(tworows, supported=["EQUIL"], consecutive="EQLNUM")
    assert "EQUIL" in string
    assert string.find("3456") > string.find("1234")


@pytest.mark.parametrize(
    "somedate, expected",
    [
        pytest.param(None, None, marks=pytest.mark.xfail(raises=TypeError)),
        pytest.param({}, None, marks=pytest.mark.xfail(raises=TypeError)),
        pytest.param(
            "",
            None,
            marks=pytest.mark.xfail(raises=ValueError, match="ISO string too short"),
        ),
        ("2021-02-01", "1 'FEB' 2021"),
        ("2021-02-01 010203", "1 'FEB' 2021 01:02:03"),
        ("2021-02-01 01:02:03", "1 'FEB' 2021 01:02:03"),
        (datetime.date(2021, 2, 1), "1 'FEB' 2021"),
        (datetime.datetime(2021, 2, 1, 0, 0, 0), "1 'FEB' 2021"),
        ("2021-02-01 000000", "1 'FEB' 2021"),
        (datetime.datetime(2021, 2, 1, 2, 3, 4), "1 'FEB' 2021 02:03:04"),
        (datetime.datetime(2021, 2, 1, 2, 3, 4, 4433), "1 'FEB' 2021 02:03:04"),
        pytest.param(
            "01/02/2021",
            None,
            marks=pytest.mark.xfail(raises=ValueError, match="Use ISO"),
        ),
    ],
)
def test_datetime_to_ecldate(somedate, expected):
    """Test conversion of datetime to Eclipse date or datetime syntax"""
    assert common.datetime_to_ecldate(somedate) == expected


def test_eclcompress():
    """Test that we can compress string using Eclipse style
    run-length encoding"""
    assert common.runlength_compress("") == ""
    assert common.runlength_compress(" ") == ""
    assert common.runlength_compress("1 2") == "1  2"
    assert common.runlength_compress("1 2", sep=" ") == "1 2"
    assert common.runlength_compress("1 2", sep="   ") == "1   2"
    assert common.runlength_compress("1") == "1"
    assert common.runlength_compress("1 1") == "2*1"
    assert common.runlength_compress("1 1 1") == "3*1"
    assert common.runlength_compress("1     1 1") == "3*1"
    assert common.runlength_compress("1  \n  1 1 2") == "3*1  2"


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


@pytest.mark.parametrize(
    "dframe, keyword, comment, renamer, drop_trailing_columns, expected",
    [
        pytest.param(
            pd.DataFrame(),
            "FOO",
            None,
            None,
            False,
            "FOO\n",
            marks=pytest.mark.xfail(raises=KeyError, match="FOO"),
            id="unknown-keyword",
        ),
        pytest.param(
            pd.DataFrame(),
            "COMPDAT",
            None,
            None,
            False,
            "COMPDAT\n",
            id="empty-frame",
        ),
        pytest.param(
            pd.DataFrame(),
            "COMPDAT",
            "foobar",
            None,
            False,
            "COMPDAT\n-- foobar\n",
            id="comment",
        ),
        pytest.param(
            pd.DataFrame(),
            "COMPDAT",
            "",
            None,
            False,
            "COMPDAT\n",
            id="comment-empty-string",
        ),
        pytest.param(
            pd.DataFrame(),
            "COMPDAT",
            "foo\nbar",
            None,
            False,
            "COMPDAT\n-- foo\n-- bar\n",
            id="comment-multiline",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1"}]),
            "COMPDAT",
            None,
            None,
            True,
            "COMPDAT\n-- WELL\n  'OP1' /\n",
            id="OP1",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1"}, {"WELL": "OP2"}]),
            "COMPDAT",
            None,
            None,
            True,
            "COMPDAT\n-- WELL\n  'OP1' /\n  'OP2' /\n",
            id="two-rows",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1", "DIR": np.nan}]),
            "COMPDAT",
            None,
            None,
            True,
            "COMPDAT\n-- WELL\n  'OP1' /\n",
            id="nan-column1",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1", "I": None}]),
            "COMPDAT",
            None,
            None,
            True,
            "COMPDAT\n-- WELL\n  'OP1' /\n",
            id="nan-column2",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1", "I": None}]),
            "COMPDAT",
            None,
            None,
            False,
            "COMPDAT\n-- WELL  I\n  'OP1' 1* /\n",
            id="nan-column2-no-drop",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1", "J": "2"}]),
            "COMPDAT",
            None,
            None,
            True,
            "COMPDAT\n-- WELL  I J\n  'OP1' 1* 2 /\n",
            # Here, the I column should not be dropped but defaulted
            id="nan-column3",
        ),
        pytest.param(
            pd.DataFrame([{"FOOWELL": "OP1"}]),
            "COMPDAT",
            None,
            {"WELL": "FOOWELL"},
            True,
            "COMPDAT\n-- FOOWELL\n  'OP1' /\n",
            id="renamer-strange-input-column-names",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1"}]),
            "COMPDAT",
            None,
            {"WELL": "FOO"},
            True,
            "COMPDAT\n-- FOO\n  'OP1' /\n",
            id="renamer-only-for-header-line",
        ),
        pytest.param(
            pd.DataFrame([{"WELL": "OP1"}]),
            "COMPDAT",
            None,
            {"bogus": "morebogus"},
            True,
            "COMPDAT\n-- WELL\n  'OP1' /\n",
            id="irrelevant-renamer",
        ),
        pytest.param(
            pd.DataFrame([{"BOGUS": "OP1"}]),
            "COMPDAT",
            None,
            None,
            True,
            "COMPDAT\n",
            id="bogus-column",
        ),
    ],
)
def test_generic_deck_table(
    dframe, keyword, comment, renamer, drop_trailing_columns, expected
):
    stringtable = common.generic_deck_table(
        dframe,
        keyword,
        comment=comment,
        renamer=renamer,
        drop_trailing_columns=drop_trailing_columns,
    )
    # Pandas 1.1.5 gives a different amount of whitespace than what
    # these tests are written for. If so, be more slack about whitespace.
    if packaging.version.parse(pd.__version__) < packaging.version.parse("1.2.0"):
        stringtable = " ".join(stringtable.split())
        assert stringtable == " ".join(expected.split())
    else:
        assert stringtable == expected
