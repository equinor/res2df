# -*- coding: utf-8 -*-
"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import pytest

import pandas as pd

from datetime import date

from ecl.eclfile import EclFile
from ecl.grid import EclGrid

from ecl2df import summary2df
from ecl2df.eclfiles import EclFiles

DATAFILE = "data/reek/eclipse/model/2_R001_REEK-0.DATA"


def test_summary2df():
    """Test that dataframes are produced"""
    eclfiles = EclFiles(DATAFILE)
    sumdf = summary2df.get_smry(eclfiles)

    assert not sumdf.empty
    assert sumdf.index.name == "DATE"
    assert len(sumdf.columns)
    assert "FOPT" in sumdf.columns


def test_main():
    """Test command line interface"""
    tmpcsvfile = ".TMP-sum.csv"
    sys.argv = ["summary2df", DATAFILE, "-o", tmpcsvfile]
    summary2df.main()

    assert os.path.exists(tmpcsvfile)
    disk_df = pd.read_csv(tmpcsvfile)
    assert not disk_df.empty
    assert "FOPT" in disk_df
    os.remove(tmpcsvfile)

def test_datenormalization():
    """Test normalization of dates, where
    dates can be ensured to be on dategrid boundaries"""
    from ecl2df.summary2df import normalize_dates

    start = date(1997, 11, 5)
    end = date(2020, 3, 2)

    assert normalize_dates(start, end, 'monthly') == \
        (date(1997, 11, 1), date(2020, 4, 1))
    assert normalize_dates(start, end, 'yearly') == \
        (date(1997, 1, 1), date(2021, 1, 1))

    # Check it does not touch already aligned dates
    assert normalize_dates(date(1997, 11, 1),
                           date(2020, 4, 1), 'monthly') == \
        (date(1997, 11, 1), date(2020, 4, 1))
    assert normalize_dates(date(1997, 1, 1),
                           date(2021, 1, 1), 'yearly') == \
        (date(1997, 1, 1), date(2021, 1, 1))

    # Check that we normalize correctly with get_smry():
    # realization-0 here has its last summary date at 2003-01-02
    eclfiles = EclFiles(DATAFILE)
    daily = summary2df.get_smry(eclfiles, column_keys='FOPT', time_index='daily')
    assert str(daily.index[-1]) == '2003-01-02'
    monthly = summary2df.get_smry(eclfiles, column_keys='FOPT', time_index='monthly')
    assert str(monthly.index[-1]) == '2003-02-01'
    yearly = summary2df.get_smry(eclfiles, column_keys='FOPT', time_index='yearly')
    assert str(yearly.index[-1]) == '2004-01-01'
