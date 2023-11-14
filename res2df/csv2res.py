#!/usr/bin/env python
"""
Convert dataframes (in res2df format) to Eclipse include files,
for selected keywords
"""

import argparse
import sys

from res2df import __version__, equil, pvt, satfunc, summary, vfp

# String constants in use for generating ERT forward model documentation:
DESCRIPTION: str = """Convert CSV files into Eclipse include files. Uses the command
line utility ``csv2res``. Run ``csv2res --help`` to see which subcommands are supported.
No options other than the output file is possible when used directly as a forward model.
When writing synthetic summary files, the ECLBASE with no filename suffix is expected
as the OUTPUT argument."""
CATEGORY: str = "utility.eclipse"
EXAMPLES: str = (
    "``FORWARD_MODEL "
    "CSV2RES(<SUBCOMMAND>=equil, <CSVFILE>=equil.csv, "
    "<OUTPUT>=eclipse/include/equil.inc)``"
    "CSV2RES(<SUBCOMMAND>=summary, <CSVFILE>=summary-monthly.csv, "
    "<OUTPUT>=eclipse/model/MONTHLYSUMMARY)``"
)


def get_parser() -> argparse.ArgumentParser:
    """Make parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "csv2res (" + __version__ + ") is a command line frontend to res2df. "
            "Documentation at https://equinor.github.io/res2df/ "
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    if sys.version_info.major >= 3 and sys.version_info.minor >= 7:
        subparsers = parser.add_subparsers(  # type: ignore
            required=True,
            dest="subcommand",
            parser_class=argparse.ArgumentParser,
        )
    else:
        subparsers = parser.add_subparsers(parser_class=argparse.ArgumentParser)

    summary_parser = subparsers.add_parser(
        "summary",
        help="Write EclSum UNSMRY files",
        description=("Write Eclipse UNSMRY files from CSV files."),
    )
    summary.fill_reverse_parser(summary_parser)
    summary_parser.set_defaults(func=summary.summary_reverse_main)

    equil_parser = subparsers.add_parser(
        "equil",
        help="Write SOLUTION include files",
        description=(
            "Write SOLUTION keywords (EQUIL, RSVD, RVVD) "
            "to Eclipse include files from CSV in res2df format."
        ),
    )
    equil.fill_reverse_parser(equil_parser)
    equil_parser.set_defaults(func=equil.equil_reverse_main)

    pvt_parser = subparsers.add_parser(
        "pvt",
        help="Write PVT include files",
        description=(
            "Write Eclipse include files from CSV files on the res2df format."
        ),
    )
    pvt.fill_reverse_parser(pvt_parser)
    pvt_parser.set_defaults(func=pvt.pvt_reverse_main)

    satfunc_parser = subparsers.add_parser(
        "satfunc",
        help="Write saturation function include files",
        description=(
            "Write saturation function include files from CSV files on "
            "the res2df format."
        ),
    )
    satfunc.fill_reverse_parser(satfunc_parser)
    satfunc_parser.set_defaults(func=satfunc.satfunc_reverse_main)

    vfp_parser = subparsers.add_parser(
        "vfp",
        help="Write VFPPROD/VFPINJ include files",
        description=(
            "Write VFPPROD/VFPINJ include files from CSV files on the res2df format."
        ),
    )
    vfp.fill_reverse_parser(vfp_parser)
    vfp_parser.set_defaults(func=vfp.vfp_reverse_main)

    return parser


def main() -> None:
    """Entry point"""
    parser = get_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
