# -*- coding: utf-8 -*-
"""Test module for layer mapping to zone names"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import ecl2df

import pytest

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_stdzoneslyr():
    ef = ecl2df.EclFiles(DATAFILE)

    zonemap = ef.get_zonemap()
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


def test_nonstandardzones(tmpdir):
    zonefile = tmpdir / "formations.lyr"
    zonefilecontent = """
-- foo
# foo
'Eiriksson'  1-10
Raude    20-30
# Difficult quote parsing above, might not run in ResInsight.
"""
    zonefile.write(zonefilecontent)
    ef = ecl2df.EclFiles(DATAFILE)
    zonemap = ef.get_zonemap(str(zonefile))
    assert zonemap[1] == "Eiriksson"


def test_nonexistingzones():
    ef = ecl2df.EclFiles(DATAFILE)
    zonemap = ef.get_zonemap("foobar")
    # (we got a warning and an empty dict)
    assert not zonemap
