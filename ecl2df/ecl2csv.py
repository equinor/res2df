#!/user/bin/env python
# -*- coding: utf-8 -*-
"""
End-user command line tool for accessing functionality
in ecl2df
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import argparse

from ecl2df import (
    grid,
    nnc,
    faults,
    equil,
    gruptree,
    rft,
    satfunc,
    summary,
    wcon,
    compdat,
)


def get_parser():
    """Make parser"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(parser_class=argparse.ArgumentParser)

    # Eclipse output files:
    grid_parser = subparsers.add_parser("grid", help="Extract grid data")
    grid.fill_parser(grid_parser)
    grid_parser.set_defaults(func=grid.grid2df_main)

    summary_parser = subparsers.add_parser("smry", help="Extract summary data")
    summary.fill_parser(summary_parser)
    summary_parser.set_defaults(func=summary.summary2df_main)

    nnc_parser = subparsers.add_parser(
        "nnc",
        help="Extract NNC data from EGRID file",
        description=(
            "Extract NNC (Non-Neighbour Connection) data from the EGRID file. "
            "Each row is one connection, with the columns I1, J1, K1 for the first cell "
            "in the cell pair, and I2, J2, K2 for the second. The transmissibility "
            "for the cell pair is in the TRAN column."
        ),
    )
    nnc.fill_parser(nnc_parser)
    nnc_parser.set_defaults(func=nnc.nnc2df_main)

    faults_parser = subparsers.add_parser("faults", help="Extract faults data")
    faults.fill_parser(faults_parser)
    faults_parser.set_defaults(func=faults.faults2df_main)

    rft_parser = subparsers.add_parser(
        "rft",
        help=("Extract RFT data from Eclipse binary output files."),
        description=(
            "Extract RFT data from Eclipse binary output files to CSV. "
            "Each row in the resulting table represents one point in a "
            "particular well at a particular time. "
            "If multisegment wells are found, associated data "
            "to a connection is merged onto the same row as additional columns. "
            "You need the Eclipse keyword WRFTPLT present in your DATA-file to get "
            "the data outputted."
        ),
    )
    rft.fill_parser(rft_parser)
    rft_parser.set_defaults(func=rft.rft2df_main)

    # Eclipse input files:
    satfunc_parser = subparsers.add_parser("satfunc", help="Extract SWOF/SGOF/etc data")
    satfunc.fill_parser(satfunc_parser)
    satfunc_parser.set_defaults(func=satfunc.satfunc2df_main)

    compdat_parser = subparsers.add_parser(
        "compdat", help="Extract COMPDAT/COMPSEGS/etc data"
    )
    compdat.fill_parser(compdat_parser)
    compdat_parser.set_defaults(func=compdat.compdat2df_main)

    equil_parser = subparsers.add_parser("equil", help="Extract EQUIL data")
    equil.fill_parser(equil_parser)
    equil_parser.set_defaults(func=equil.equil2df_main)

    gruptree_parser = subparsers.add_parser("gruptree", help="Extract GRUPTREE data")
    gruptree.fill_parser(gruptree_parser)
    gruptree_parser.set_defaults(func=gruptree.gruptree2df_main)

    wcon_parser = subparsers.add_parser("wcon", help="Extract well control data")
    wcon.fill_parser(wcon_parser)
    wcon_parser.set_defaults(func=wcon.wcon2df_main)

    return parser


def main():
    """Entry point"""
    parser = get_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
