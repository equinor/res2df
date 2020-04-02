#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convert dataframes (in ecl2df format) to Eclipse include files,
for selected keywords
"""

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import sys

import argparse

import six

from ecl2df import pvt

from ecl2df import __version__


def get_parser():
    """Make parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "csv2ecl (" + __version__ + ") is a command line frontend to ecl2df. "
            "Documentation at https://equinor.github.io/ecl2df/ "
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    if sys.version_info.major >= 3 and sys.version_info.minor >= 7:
        subparsers = parser.add_subparsers(
            required=True, dest="subcommand", parser_class=argparse.ArgumentParser
        )
    else:
        subparsers = parser.add_subparsers(parser_class=argparse.ArgumentParser)

    pvt_parser = subparsers.add_parser(
        "pvt",
        help="Write PVT include files",
        description=(
            "Write Eclipse include files from dataframes/CSV files on "
            "the ecl2df format."
        ),
    )
    pvt.fill_reverse_parser(pvt_parser)
    pvt_parser.set_defaults(func=pvt.pvt_reverse_main)
    return parser


def main():
    """Entry point"""
    parser = get_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
