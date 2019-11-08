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


def test_stdlayerslyr():
    ef = ecl2df.EclFiles(DATAFILE)

    layersmap = ef.get_layermap()
    assert isinstance(layersmap, dict)
    assert layersmap[3] == "UpperReek"
    assert layersmap[10] == "MidReek"
    assert layersmap[11] == "LowerReek"
    with pytest.raises(KeyError):
        layersmap[0]
    with pytest.raises(KeyError):
        layersmap["foo"]
    with pytest.raises(KeyError):
        layersmap[-10]
    assert len(layersmap) == 15


def test_nonstandardlayers(tmpdir):
    layerfile = tmpdir / "formations.lyr"
    layerfilecontent = """
-- foo
# foo
'Eiriksson'  1-10
Raude    20-30
# Difficult quote parsing above, might not run in ResInsight.
"""
    layerfile.write(layerfilecontent)
    ef = ecl2df.EclFiles(DATAFILE)
    layersmap = ef.get_layermap(str(layerfile))
    assert layersmap[1] == "Eiriksson"


def test_nonexistinglayers():
    ef = ecl2df.EclFiles(DATAFILE)
    layersmap = ef.get_layermap("foobar")
    # (we got a warning and an empty dict)
    assert not layersmap
