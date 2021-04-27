"""Test module for layer mapping to zone names"""

import pytest
from pathlib import Path

import ecl2df


TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_stdzoneslyr():
    """Test that we can read zones if the zonemap is in a standard location.

    The eclfiles object defines what is the standard location for the file, while
    the actual parsing is done in ecl2df.common.parse_zonemapfile()
    """
    eclfiles = ecl2df.EclFiles(DATAFILE)

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
    eclfiles = ecl2df.EclFiles(DATAFILE)
    zonemap = eclfiles.get_zonemap("foobar")
    # (we got a warning and an empty dict)
    assert not zonemap


def test_errors(tmpdir, caplog):
    zonefile = tmpdir / "zonemap.lyr"
    zonefile.write_text(
        """
foo
""",
        encoding="utf-8",
    )
    assert ecl2df.common.parse_zonemapfile(zonefile) is None
    assert "Could not parse zonemapfile" in caplog.text
    assert "Failed on content: foo" in caplog.text

    zonefile = tmpdir / "zonemap.lyr"
    zonefile.write_text(
        """
valid 1-2
foo 1 2 3
""",
        encoding="utf-8",
    )
    assert ecl2df.common.parse_zonemapfile(zonefile) is None
    assert "Failed on content: foo 1 2 3" in caplog.text

    zonefile = tmpdir / "zonemap.lyr"
    zonefile.write_text(
        """
valid 1-2 stray
""",
        encoding="utf-8",
    )
    assert ecl2df.EclFiles(DATAFILE).get_zonemap(str(zonefile)) is None
    assert "Failed on content: valid 1-2 stray" in caplog.text


def test_spaces_dashes(tmpdir):
    """Ensure we support dashes around dashes"""
    zonefile = tmpdir / "zonemap.lyr"
    zonefile.write_text(
        """
-- Layer table for 83 layer simulation model xxxx
'UT3_3'          1 -     15
'UT3_2'          16 -   20
'UT3_1'         21 -    21
'UT2'           22 -   23
'UT1_2'         24 -   37
'UT1_1'         38 -   46 -- thistextisignored
'MT2_2'         47 -   71
""",
        encoding="utf-8",
    )
    zonemap = ecl2df.common.parse_zonemapfile(zonefile)
    assert zonemap
    assert len(zonemap) == 71
    assert zonemap[25] == "UT1_2"


def test_nonstandardzones(tmpdir):
    """Test that we can read zones from a specific filename"""
    zonefile = tmpdir / "formations.lyr"
    zonefilecontent = """
-- foo
# foo
'Eiriksson'  1-10
 Raude    20-30

# Difficult quote parsing above, might not run in ResInsight.
"""
    zonefile.write(zonefilecontent)
    zonemap = ecl2df.common.parse_zonemapfile(zonefile)
    assert 0 not in zonemap
    assert zonemap[1] == "Eiriksson"
    assert zonemap[10] == "Eiriksson"
    assert 11 not in zonemap
    assert 19 not in zonemap
    assert zonemap[20] == "Raude"
    assert zonemap[30] == "Raude"
    assert len(zonemap) == 21
