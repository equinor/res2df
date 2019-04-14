# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from ecl2df import nnc2df
from ecl.eclfile import EclFile
from ecl.grid import EclGrid

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"

def test_data2eclfiles():
    result = nnc2df.data2eclfiles(DATAFILE)

    assert isinstance(result, tuple)
    assert isinstance(result[0], EclFile)
    assert isinstance(result[1], EclGrid)
    assert isinstance(result[2], EclFile)


def test_nnc2df():
    eclfiles = nnc2df.data2eclfiles(DATAFILE)
    nncdf = nnc2df.nnc2df(eclfiles)

    assert not nncdf.empty
    assert 'I1' in nncdf
    assert 'J1' in nncdf
    assert 'K1' in nncdf
    assert 'I2' in nncdf
    assert 'J2' in nncdf
    assert 'K2' in nncdf
    assert 'TRAN' in nncdf

