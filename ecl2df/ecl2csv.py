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
    grid2df,
    nnc2df,
    faults2df,
    equil2df,
    gruptree2df,
    rft2df,
    satfunc2df,
    summary2df,
    wcon2df,
    compdat2df,
)


def get_parser():
    """Make parser"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(parser_class=argparse.ArgumentParser)

    # Eclipse output files:
    grid_parser = subparsers.add_parser("grid", help="Extract grid data")
    grid2df.fill_parser(grid_parser)
    grid_parser.set_defaults(func=grid2df.grid2df_main)

    summary_parser = subparsers.add_parser("smry", help="Extract summary data")
    summary2df.fill_parser(summary_parser)
    summary_parser.set_defaults(func=summary2df.summary2df_main)

    nnc_parser = subparsers.add_parser("nnc", help="Extract nnc data")
    nnc2df.fill_parser(nnc_parser)
    nnc_parser.set_defaults(func=nnc2df.nnc2df_main)

    faults_parser = subparsers.add_parser("faults", help="Extract faults data")
    faults2df.fill_parser(faults_parser)
    faults_parser.set_defaults(func=faults2df.faults2df_main)

    rft_parser = subparsers.add_parser("rft", help="Extract RFT data")
    rft2df.fill_parser(rft_parser)
    rft_parser.set_defaults(func=rft2df.rft2df_main)

    # Eclipse input files:
    satfunc_parser = subparsers.add_parser("satfunc", help="Extract SWOF/SGOF/etc data")
    satfunc2df.fill_parser(satfunc_parser)
    satfunc_parser.set_defaults(func=satfunc2df.satfunc2df_main)

    compdat_parser = subparsers.add_parser(
        "compdat", help="Extract COMPDAT/COMPSEGS/etc data"
    )
    compdat2df.fill_parser(compdat_parser)
    compdat_parser.set_defaults(func=compdat2df.compdat2df_main)

    equil_parser = subparsers.add_parser("equil", help="Extract EQUIL data")
    equil2df.fill_parser(equil_parser)
    equil_parser.set_defaults(func=equil2df.equil2df_main)

    gruptree_parser = subparsers.add_parser("gruptree", help="Extract GRUPTREE data")
    gruptree2df.fill_parser(gruptree_parser)
    gruptree_parser.set_defaults(func=gruptree2df.gruptree2df_main)

    wcon_parser = subparsers.add_parser("wcon", help="Extract well control data")
    wcon2df.fill_parser(wcon_parser)
    wcon_parser.set_defaults(func=wcon2df.wcon2df_main)

    return parser


def main():
    """Entry point"""
    parser = get_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
