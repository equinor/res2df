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

from ecl2df import grid2df, nnc2df


def main():
    """Entry-point"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    
    grid_parser = subparsers.add_parser("grid", help="Extract grid data")
    grid2df.fill_parser(grid_parser)
    grid_parser.set_defaults(func=grid2df.grid2df_main)

    nnc_parser = subparsers.add_parser("nnc", help="Extract nnc data")
    nnc2df.fill_parser(nnc_parser)
    nnc_parser.set_defaults(func=nnc2df.nnc2df_main)
    
    args = parser.parse_args()
    args.func(args)
    

if __name__ == "__main__":
    main()
