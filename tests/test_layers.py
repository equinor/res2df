# -*- coding: utf-8 -*-
"""Test module for layer mapping to zone names"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import ecl2df

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_stdlayerslyr():
    ef = ecl2df.EclFiles(DATAFILE)

    layersmap = ef.get_layermap()
    assert isinstance(layersmap, dict)
    assert layersmap[3] == "UpperReek"
    assert layersmap[10] == "MidReek"
    assert layersmap[11] == "LowerReek"
    assert len(layersmap) == 15
