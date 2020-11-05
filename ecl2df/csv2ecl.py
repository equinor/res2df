#!/usr/bin/env python
"""
Convert dataframes (in ecl2df format) to Eclipse include files,
for selected keywords
"""

import sys

import argparse

from ecl2df import pvt, equil, satfunc

from ecl2df import __version__

# String constants in use for generating ERT forward model documentation:
DESCRIPTION = """Convert CSV files into Eclipse include files. Uses the command
line utility ``csv2ecl``. Run ``csv2ecl --help`` to see which subcommands are supported.
No options other than the output file is possible when
used directly as a forward model."""
CATEGORY = "utility.eclipse"
EXAMPLES = (
    "``FORWARD_MODEL "
    "CSV2ECL(<SUBCOMMAND>=equil, <CSVFILE>=equil.csv, "
    "<OUTPUT>=eclipse/include/equil.inc)``"
)


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

    equil_parser = subparsers.add_parser(
        "equil",
        help="Write SOLUTION include files",
        description=(
            "Write SOLUTION keywords (EQUIL, RSVD, RVVD) "
            "to Eclipse include files from CSV in ecl2df format."
        ),
    )
    equil.fill_reverse_parser(equil_parser)
    equil_parser.set_defaults(func=equil.equil_reverse_main)

    pvt_parser = subparsers.add_parser(
        "pvt",
        help="Write PVT include files",
        description=(
            "Write Eclipse include files from CSV files on the ecl2df format."
        ),
    )
    pvt.fill_reverse_parser(pvt_parser)
    pvt_parser.set_defaults(func=pvt.pvt_reverse_main)

    satfunc_parser = subparsers.add_parser(
        "satfunc",
        help="Write saturation function include files",
        description=(
            "Write saturation function include files from CSV files on "
            "the ecl2df format."
        ),
    )
    satfunc.fill_reverse_parser(satfunc_parser)
    satfunc_parser.set_defaults(func=satfunc.satfunc_reverse_main)

    return parser


def main():
    """Entry point"""
    parser = get_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
