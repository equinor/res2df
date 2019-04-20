#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract grid information from Eclipse output files as Dataframes.

Each cell in the grid correspond to one row.

For grid cells, x, y, z for cell centre and volume is available as
geometric information. Static data (properties) can be merged from 
the INIT file, and dynamic data can be merged from the Restart (UNRST)
file.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import argparse
import datetime
import dateutil.parser
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

    Non-unified restart format is not supported.

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
            rstfilename,
        )

    return (EclFile(egridfilename), EclGrid(egridfilename), EclFile(initfilename), None)


def rstdates(rstfile, rstfilename):
    """Return a list of datetime objects for the available dates in the RST file"""
    report_indices = EclFile.file_report_list(rstfilename)
    return [rstfile.iget_restart_sim_time(index).date() for index in report_indices]


def rst2df(rstfile, rstfilename, activecells, date, dateinheaders=False):
    """Return a dataframe with dynamic data from the restart file
    for each cell, at a particular date. 

    Args:
        rstfile: EclFile object for the UNRST file
        rstfilename: str with UNRST filename
        activecells: int with the number of active cells, 
            typically taken from EclGrid.getNumActive().
            Only vectors with this lengths can be added
            to the grid dataframe.
        date: datetime.date or list of datetime.date, must
            correspond to an existing date. If list, it
            forces dateinheaders to be True.
            Can also be string, then the mnenomics
            'first', 'last', 'all', are supported, or ISO
            date formats.
        dateinheaders: boolean on whether the date should
            be added to the column headers. Instead of 
            SGAS as a column header, you get SGAS@YYYY-MM-DD.
    """
    # First task is to determine the restart index to extract
    # data for:
    dates = rstdates(rstfile, rstfilename)

    supportedmnemonics = ["first", "last", "all"]

    # After this control block, chosendates is a list of dates
    # we should extract, and which exists in UNRST.
    if isinstance(date, str):
        if date not in supportedmnemonics:
            # Try to parse as ISO date:
            try:
                isodate = dateutil.parser.isoparse(date).date()
                if isodate not in dates:
                    raise ValueError("date " + isodate + " not found in UNRST file")
                else:
                    chosendates = [isodate]
            except ValueError:
                raise ValueError("date " + date + " not understood")
        else:
            if date == "first":
                chosendates = [dates[0]]
            elif date == "last":
                chosendates = [dates[-1]]
            elif date == "all":
                chosendates = dates
    elif isinstance(date, datetime.date):
        chosendates = [date]
    elif isinstance(date, datetime.datetime):
        chosendates = [date.date()]
    elif isinstance(date, list):
        chosendates = [x for x in date if x in dates]
        if not chosendates:
            raise ValueError("None of the requested dates were found")
        elif len(chosendates) < len(dates):
            print("Warning: Not all dates found in UNRST\n")
    else:
        raise ValueError("date " + str(date) + " not understood")

    rstindices = [dates.index(x) for x in chosendates]

    # Determine the available restart vectors, we only include
    # those with correct length, meaning that they are defined
    # for all active cells:
    rstvectors = []
    for vec in rstfile.headers:
        if vec[1] == activecells:
            rstvectors.append(vec[0])
    rstvectors = list(set(rstvectors))  # Make unique list
    # Note that all of these might not exist at all timesteps.
    print(rstvectors)

    rst_dfs = []
    for rstindex in rstindices:
        # Filter the rst vectors once more, all of them
        # might not be available at all timesteps:
        present_rstvectors = []
        for vec in rstvectors:
            if rstfile.iget_named_kw(vec, rstindex):
                present_rstvectors.append(vec)

        if not present_rstvectors:
            continue

        # Make the dataframe
        rst_df = pd.DataFrame(
            columns=rstvectors,
            data=np.hstack(
                [
                    rstfile.iget_named_kw(vec, rstindex).numpyView().reshape(-1, 1)
                    for vec in present_rstvectors
                ]
            ),
        )

        # Tag the column names if requested, or if multiple rst indices
        # are asked for
        if dateinheaders or len(rstindices) > 1:
            datestr = "@" + chosendates[rstindices.index(rstindex)].isoformat()
            rst_df.columns = [colname + datestr for colname in rst_df.columns]

        rst_dfs.append(rst_df)

    if not rst_dfs:
        return pd.DataFrame()

    return pd.concat(rst_dfs, axis=1)


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
