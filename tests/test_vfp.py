"""Test module for vfp2df"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ecl2df import ecl2csv, vfp
from ecl2df.eclfiles import EclFiles

try:
    import opm  # noqa
except ImportError:
    pytest.skip(
        "OPM is not installed, nothing relevant in here then",
        allow_module_level=True,
    )

TESTDIR = Path(__file__).absolute().parent 
VFPDIR = str(TESTDIR) + '/data/vfp/'
VFPPRODFILES = ['/test_vfpprod.Ecl', 'test_vfpprod_defaulted.Ecl']
VFPINJFILES = ['test_vfpinj.Ecl','test_vfpinj_defaulted.Ecl']
CSVPRODFILES = ['test_vfpprod.csv', 'test_vfpprod_defaulted.csv']
CSVINJFILES = ['test_vfpinj.csv','test_vfpinj_defaulted.csv']

def test_vfp2df():
    """ Test that correct dataframes are produced"""

    for vfpfile in VFPPRODFILES:
        vfp_filename = VFPDIR + vfpfile
        print(vfp_filename)
        eclfiles = EclFiles(vfp_filename)
        vfp_df = vfp.df(eclfiles,keywords=['VFPPROD'])
        assert not vfp_df.empty
        vfp_inc_string = vfp.df2ecl(vfp_df,keywords=['VFPPROD'])
        vfp_df_from_inc = vfp.df(vfp_inc_string,keywords=['VFPPROD'])
        assert not vfp_df_from_inc.empty
        pd.testing.assert_frame_equal(vfp_df, vfp_df_from_inc, check_dtype=True)
    for vfpfile in VFPINJFILES:
        vfp_filename = VFPDIR + vfpfile
        eclfiles = EclFiles(vfp_filename)
        vfp_df = vfp.df(eclfiles,keywords=['VFPINJ'])
        assert not vfp_df.empty
        vfp_inc_string = vfp.df2ecl(vfp_df,keywords=['VFPINJ'])
        vfp_df_from_inc = vfp.df(vfp_inc_string,keywords=['VFPINJ'])
        assert not vfp_df_from_inc.empty
        pd.testing.assert_frame_equal(vfp_df, vfp_df_from_inc, check_dtype=True)   
    
def test_df2ecl(tmp_path):
    """Test that we can write include files to disk"""
    
    for i, vfpfile in enumerate(VFPPRODFILES):
        vfp_filename = VFPDIR + vfpfile
        eclfiles = EclFiles(vfp_filename)
        vfp_df = vfp.df(eclfiles,keywords=['VFPPROD'])
        csv_filename = VFPDIR + CSVPRODFILES[i]
        disk_df = pd.read_csv(csv_filename)
        disk_df.index = vfp_df.index
        assert len(vfp_df) == len(disk_df)
        print(vfp_df['RATE'])
        print(disk_df['RATE'])
        pd.testing.assert_frame_equal(vfp_df, disk_df, check_dtype=False)
        
    for i, vfpfile in enumerate(VFPINJFILES):
        vfp_filename = VFPDIR + vfpfile
        eclfiles = EclFiles(vfp_filename)
        vfp_df = vfp.df(eclfiles,keywords=['VFPINJ'])
        csv_filename = VFPDIR + CSVINJFILES[i]
        disk_df = pd.read_csv(csv_filename)
        disk_df.index = vfp_df.index
        assert len(vfp_df) == len(disk_df)
        pd.testing.assert_frame_equal(vfp_df, disk_df, check_dtype=False)
