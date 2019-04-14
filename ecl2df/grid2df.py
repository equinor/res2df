#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract grid information from Eclipse output files as Dataframes.

Each cell in the grid correspond to one row.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import argparse
import numpy as np
import pandas as pd

from ecl.eclfile import EclFile
from ecl.grid import EclGrid


def data2eclfiles(eclbase):
    """Loads INIT and GRID files from the supplied eclbase

    The eclbase should be the path to the Eclipse DATA file,
    with or without the .DATA extension

    Fails if EGRID or INIT is not present.
 
    If RST file is present, a EclFile is returned in the fourth
    argument, if not, the fourth element is None.

    Returns:
        tuple with EclFile from EGRID, EclGrid from EGRID
           and EclFile from INIT. Fourth element is None, or
           EclFile from UNRST
    """

    def rreplace(pat, sub, string):
        """Variant of str.replace() that only replaces at the end of the string"""
        return string[0 : -len(pat)] + sub if string.endswith(pat) else string

    eclbase = rreplace(".DATA", "", eclbase)
    eclbase = rreplace(".", "", eclbase)

    egridfilename = eclbase + ".EGRID"
    initfilename = eclbase + ".INIT"
    rstfilename = eclbase + ".UNRST"

    if not os.path.exists(egridfilename):
        raise IOError(egridfilename + " not found")
    if not os.path.exists(initfilename):
        raise IOError(initfilename + " not found")

    if os.path.exists(rstfilename):
        return (
            EclFile(egridfilename),
            EclGrid(egridfilename),
            EclFile(initfilename),
            EclFile(rstfilename),
        )

    return (EclFile(egridfilename), EclGrid(egridfilename), EclFile(initfilename), None)


def gridgeometry2df(eclfiles):
    """Produce a Pandas Dataframe with Eclipse gridgeometry

    Order is significant, and is determined by the order from libecl, and used
    when merging with other dataframes with cell-data.

    Args:
        eclfiles: tuple with EclFile (EGRID), EclGrid (EGRID). Tuple may contain
            extra elements, which will be ignored.

    Returns:
        pd.DataFrame.
    """
    if not eclfiles:
        raise ValueError
    egrid_file = eclfiles[0]
    grid = eclfiles[1]

    if not egrid_file or not grid:
        raise ValueError("No EGRID file supplied")

    index_frame = grid.export_index(active_only=True)
    ijk = index_frame.values[:, 0:3] + 1  # ijk from ecl.grid is off by one

    xyz = grid.export_position(index_frame)
    vol = grid.export_volume(index_frame)
    grid_df = pd.DataFrame(
        index=index_frame["active"],
        columns=["i", "j", "k", "x", "y", "z", "volume"],
        data=np.hstack((ijk, xyz, vol.reshape(-1, 1))),
    )
    # Type conversion, hstack maybe ruined the datatypes..
    grid_df["i"] = grid_df["i"].astype(int)
    grid_df["j"] = grid_df["j"].astype(int)
    grid_df["k"] = grid_df["k"].astype(int)

    # Column names should be uppercase
    grid_df.columns = [x.upper() for x in grid_df.columns]

    return grid_df


def init2df(init, active_cells):
    """Extract information from INIT file with cell data

    Order is significant, as index is used for merging

    Args:
        init_file: EclFile for the INIT object
        active_cells: int, The number of active cells each vector is required to have
            Other vectors will be dropped.
    """
    # Build list of vector names to include:
    vectors = []
    for vector in init.headers:
        if vector[1] == active_cells:
            vectors.append(vector[0])

    init_df = pd.DataFrame(
        columns=vectors,
        data=np.hstack(
            [init.iget_named_kw(vec, 0).numpyView().reshape(-1, 1) for vec in vectors]
        ),
    )
    return init_df


# Remaining functions are for the command line interface


def merge_gridframes(grid_df, init_df, rst_dfs=None):
    """Merge dataframes with grid data"""
    return pd.concat([grid_df, init_df], axis=1, sort=False)


def parse_args():
    """Parse sys.argv using argparse"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "DATAFILE",
        help="Name of Eclipse DATA file. " + "INIT and EGRID file must lie alongside.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Name of output csv file.",
        default="eclgrid.csv",
    )
    return parser.parse_args()


def main():
    """Entry-point for module, for command line utility"""
    args = parse_args()
    eclfiles = data2eclfiles(args.DATAFILE)
    gridgeom = gridgeometry2df(eclfiles)
    initdf = init2df(eclfiles[2], eclfiles[1].getNumActive())
    grid_df = merge_gridframes(gridgeom, initdf)
    grid_df.to_csv(args.output, index=False)
    print("Wrote to " + args.output)
