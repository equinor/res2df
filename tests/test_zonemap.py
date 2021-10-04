"""Test module for layer mapping to zone names"""

from pathlib import Path

import pandas as pd
import pytest

import ecl2df

TESTDIR = Path(__file__).absolute().parent
REEK = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_stdzoneslyr():
    """Test that we can read zones if the zonemap is in a standard location.

    The eclfiles object defines what is the standard location for the file, while
    the actual parsing is done in ecl2df.common.parse_lyrfile() and
    converted to zonemap in common.convert_lyrlist_to_zonemap()
    """
    eclfiles = ecl2df.EclFiles(REEK)

    zonemap = eclfiles.get_zonemap()
    assert isinstance(zonemap, dict)
    assert zonemap[3] == "UpperReek"
    assert zonemap[10] == "MidReek"
    assert zonemap[11] == "LowerReek"
    with pytest.raises(KeyError):
        assert zonemap[0]
    with pytest.raises(KeyError):
        assert zonemap["foo"]
    with pytest.raises(KeyError):
        assert zonemap[-10]
    assert len(zonemap) == 15


def test_nonexistingzones():
    """Test an Eclipse case with non-existing zonemap (i.e. no zonemap file
    in the standard location)"""
    eclfiles = ecl2df.EclFiles(REEK)
    zonemap = eclfiles.get_zonemap("foobar")
    # (we got a warning and an empty dict)
    assert not zonemap


def test_errors(tmp_path, caplog):
    """Test in lyr parse function return correct errors"""
    lyrfile = tmp_path / "formations.lyr"
    lyrfile.write_text(
        """
foo
""",
        encoding="utf-8",
    )
    assert ecl2df.common.parse_lyrfile(lyrfile) is None
    assert "Could not parse lyr file" in caplog.text
    assert "Failed on content: foo" in caplog.text

    lyrfile = tmp_path / "formations.lyr"
    lyrfile.write_text(
        """
valid 1-2
foo 1 2 3
""",
        encoding="utf-8",
    )
    assert ecl2df.common.parse_lyrfile(lyrfile) is None
    assert "Failed on content: foo 1 2 3" in caplog.text

    lyrfile = tmp_path / "formations.lyr"
    lyrfile.write_text(
        """
foo 2-1
""",
        encoding="utf-8",
    )
    assert ecl2df.EclFiles(REEK).get_zonemap(str(lyrfile)) is None
    assert "From_layer higher than to_layer" in caplog.text

    lyrfile = tmp_path / "formations.lyr"
    lyrfile.write_text(
        """
valid 1-2 #FFE5F7
foo   3- 4 #FFGGHH
""",
        encoding="utf-8",
    )
    assert ecl2df.EclFiles(REEK).get_zonemap(str(lyrfile)) is None
    assert "Failed on content: foo   3- 4 #FFGGHH" in caplog.text

    lyrfile = tmp_path / "formations.lyr"
    lyrfile.write_text(
        """
valid 1-2 #FFE5F7
foo   3- 4 bluez
""",
        encoding="utf-8",
    )
    assert ecl2df.EclFiles(REEK).get_zonemap(str(lyrfile)) is None
    assert "Failed on content: foo   3- 4 bluez" in caplog.text

    lyrfile.write_text(
        """
invalid 1-2-3
""",
        encoding="utf-8",
    )
    assert ecl2df.EclFiles(REEK).get_zonemap(str(lyrfile)) is None


def test_lyrlist_format(tmp_path):
    """Ensure the lyr file is parsed correctly"""
    lyrfile = tmp_path / "formations.lyr"
    lyrfile.write_text(
        """
-- Some text
'ZoneA'          1 -     5  #FFE5F7
'ZoneB'          6-     10  --no color
'ZoneC'          11-15    blue
'ZoneD'         3          #fbb
'ZoneE'         19     -20
'ZoneF'         21-22  CORNFLOWERBLUE
""",
        encoding="utf-8",
    )
    lyrlist = ecl2df.common.parse_lyrfile(lyrfile)

    assert lyrlist == [
        {"name": "ZoneA", "from_layer": 1, "to_layer": 5, "color": "#FFE5F7"},
        {
            "name": "ZoneB",
            "from_layer": 6,
            "to_layer": 10,
        },
        {"name": "ZoneC", "from_layer": 11, "to_layer": 15, "color": "blue"},
        {"name": "ZoneD", "span": 3, "color": "#fbb"},
        {
            "name": "ZoneE",
            "from_layer": 19,
            "to_layer": 20,
        },
        {"name": "ZoneF", "from_layer": 21, "to_layer": 22, "color": "CORNFLOWERBLUE"},
    ]


def test_convert_lyrlist_to_zonemap(tmp_path):
    """Test common.covert_lyrlist_to_zonemap()"""
    lyrfile = tmp_path / "formations.lyr"
    lyrfile.write_text(
        """
-- Some text
'ZoneA'          1 -     5
'ZoneB'         5
'ZoneC'         11-20
""",
        encoding="utf-8",
    )
    lyrlist = ecl2df.common.parse_lyrfile(lyrfile)
    zonemap = ecl2df.common.convert_lyrlist_to_zonemap(lyrlist)
    assert zonemap
    assert len(lyrlist) == 3
    assert len(zonemap) == 20
    assert zonemap[10] == "ZoneB"
    assert zonemap[20] == "ZoneC"


def test_nonstandardzones(tmp_path):
    """Test that we can read zones from a specific filename"""
    lyrfile = tmp_path / "formations.lyr"
    lyrfilecontent = """
-- foo
# foo
'Eiriksson'  1-10
 Raude    20-30

# Difficult quote parsing above, might not run in ResInsight.
"""
    lyrfile.write_text(lyrfilecontent)
    lyrlist = ecl2df.common.parse_lyrfile(lyrfile)
    zonemap = ecl2df.common.convert_lyrlist_to_zonemap(lyrlist)
    assert 0 not in zonemap
    assert zonemap[1] == "Eiriksson"
    assert zonemap[10] == "Eiriksson"
    assert 11 not in zonemap
    assert 19 not in zonemap
    assert zonemap[20] == "Raude"
    assert zonemap[30] == "Raude"
    assert len(zonemap) == 21


@pytest.mark.parametrize(
    "dframe, zonedict, zoneheader, kname, expected_df",
    [
        (
            pd.DataFrame([{}]),
            {},
            "ZONE",
            "K",
            pd.DataFrame([{}]),
        ),
        (
            pd.DataFrame([{"K": 1}]),
            {},
            "ZONE",
            "K",
            pd.DataFrame([{"K": 1}]),
        ),
        (
            pd.DataFrame([{"K": 1}]),
            {1: "FOO"},
            "ZONE",
            "K",
            pd.DataFrame([{"K": 1, "ZONE": "FOO"}]),
        ),
        (
            pd.DataFrame([{"KK": 1}]),
            {1: "FOO"},
            "ZONE",
            "KK",
            pd.DataFrame([{"KK": 1, "ZONE": "FOO"}]),
        ),
        (
            pd.DataFrame([{"K": 1}]),
            {1: "FOO"},
            "ZONE",
            "KK",
            pd.DataFrame([{"K": 1}]),
        ),
        (
            pd.DataFrame([{"K": 1}]),
            {1: "FOO"},
            "SUBZONE",
            "K",
            pd.DataFrame([{"K": 1, "SUBZONE": "FOO"}]),
        ),
        (
            pd.DataFrame([{"K": 1}]),
            {2: "FOO"},
            "ZONE",
            "K",
            pd.DataFrame([{"K": 1, "ZONE": None}]),
        ),
        (
            pd.DataFrame([{"K": 1}, {"K": 2}]),
            {2: "FOO"},
            "ZONE",
            "K",
            pd.DataFrame([{"K": 1, "ZONE": None}, {"K": 2, "ZONE": "FOO"}]),
        ),
    ],
)
def test_merge_zones(dframe, zonedict, zoneheader, kname, expected_df):
    pd.testing.assert_frame_equal(
        ecl2df.common.merge_zones(dframe, zonedict, zoneheader, kname),
        expected_df,
        check_like=True,
    )


def test_repeated_merge_zone():
    """Merging zone information into a frame where the column already
    exists should not modify the frame."""

    dframe = pd.DataFrame([{"K1": 1, "ZONE": "upper"}])
    pd.testing.assert_frame_equal(
        ecl2df.common.merge_zones(dframe, {1: "upper"}, "ZONE"), dframe
    )
    pd.testing.assert_frame_equal(
        ecl2df.common.merge_zones(dframe, {1: "lower"}, "ZONE"), dframe
    )
