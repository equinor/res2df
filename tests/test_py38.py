"""Test module for nnc2df"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging
import os
import sys

import pandas as pd

from ecl2df import nnc, faults, ecl2csv
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")

logging.basicConfig()
logger = logging.getLogger(__name__)



def test_nncpy37():
    eclfiles = EclFiles(DATAFILE)

    egrid_file = eclfiles.get_egridfile()
    egrid_grid = eclfiles.get_egrid()
    init_file = eclfiles.get_initfile()

    print(egrid_file)
    print(egrid_grid)
    print(init_file)


    nnc1 = egrid_file["NNC1"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "NNC1: len: %d, min: %d, max: %d (global indices)",
        len(nnc1),
        min(nnc1),
        max(nnc1),
    )
    idx_cols1 = ["I1", "J1", "K1"]
    nnc1_df = pd.DataFrame(
        columns=idx_cols1, data=[egrid_grid.get_ijk(global_index=x - 1) for x in nnc1]
    )
    # Returned indices from get_ijk are zero-based, convert to 1-based indices
    nnc1_df[idx_cols1] = nnc1_df[idx_cols1] + 1
    print(nnc1_df.head())

    # Grid indices for second cell in cell pairs
    nnc2 = egrid_file["NNC2"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "NNC2: len: %d, min: %d, max: %d (global indices)",
        len(nnc2),
        min(nnc2),
        max(nnc2),
    )
    idx_cols2 = ["I2", "J2", "K2"]
    nnc2_df = pd.DataFrame(
        columns=idx_cols2, data=[egrid_grid.get_ijk(global_index=x - 1) for x in nnc2]
    )
    nnc2_df[idx_cols2] = nnc2_df[idx_cols2] + 1
    print(nnc2_df.head())

    # Obtain transmissibility value, corresponding to the cell pairs above.
    tran = init_file["TRANNNC"][0].numpy_view().reshape(-1, 1)
    logger.info(
        "TRANNNC: len: %d, min: %f, max: %f, mean=%f",
        len(tran),
        min(tran),
        max(tran),
        tran.mean(),
    )
    tran_df = pd.DataFrame(columns=["TRAN"], data=tran)
    print(tran_df.head())

