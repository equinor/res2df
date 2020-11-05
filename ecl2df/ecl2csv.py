#!/usr/bin/env python
"""
End-user command line tool for accessing functionality
in ecl2df
"""
import sys

import argparse

from ecl2df import (
    compdat,
    equil,
    faults,
    fipreports,
    grid,
    gruptree,
    nnc,
    pillars,
    pvt,
    rft,
    satfunc,
    summary,
    trans,
    wcon,
)

from ecl2df import __version__

# String constants in use for generating ERT forward model documentation:
DESCRIPTION = """Convert Eclipse input and output files into CSV files.
Uses the command line utility ``ecl2csv``. Run ``ecl2csv --help`` to see
which subcommands are supported. It is not possible to supply extra
options to ecl2csv through this forward model."""
CATEGORY = "utility.eclipse"
EXAMPLES = "``FORWARD_MODEL ECL2CSV(<SUBCOMMAND>=equil, <OUTPUT>=equil.csv)``"


def get_parser():
    """Make parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "ecl2csv (" + __version__ + ") is a command line frontend to ecl2df. "
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

    # Eclipse output files:
    grid_parser = subparsers.add_parser(
        "grid",
        help=("Extract grid data with properties"),
        description=(
            "Each cell is represented by "
            "one row of data. The coordinates are in the X, Y, and Z columns "
            "and represent the grid centre. Volume pr. cell is added "
            "and all INIT and UNRST data can be added to the rows"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    grid.fill_parser(grid_parser)
    grid_parser.set_defaults(func=grid.grid_main)

    summary_parser = subparsers.add_parser(
        "summary",
        help=("Extract summary data"),
        description=(
            "This is the time-dependent data for "
            "field production data, well profiles etc. Each row contains data "
            "for one point in time"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    summary.fill_parser(summary_parser)
    summary_parser.set_defaults(func=summary.summary_main)

    nnc_parser = subparsers.add_parser(
        "nnc",
        help="Extract NNC data from EGRID file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Extract NNC (Non-Neighbour Connection) data from the EGRID file. "
            "Each row is one connection, with the columns I1, J1, K1 for the first "
            "cell in the cell pair, and I2, J2, K2 for the second. The "
            "transmissibility for the cell pair is in the TRAN column. "
            "See also the trans subcommand."
        ),
    )
    nnc.fill_parser(nnc_parser)
    nnc_parser.set_defaults(func=nnc.nnc_main)

    faults_parser = subparsers.add_parser(
        "faults",
        help="Extract data from the FAULTS keyword",
        description=(
            "Each row represents a particular cell and a face and the name of the fault"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    faults.fill_parser(faults_parser)
    faults_parser.set_defaults(func=faults.faults_main)

    trans_parser = subparsers.add_parser(
        "trans",
        help="Extract transmissibilities from EGRID file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Extract transmissibilities (TRANX, TRANY, TRANZ) from Eclipse "
            "binary output files. Each row represent a connection between a cell pair "
            "(I1, J1, K1) and (I2, J2, K2). It is possible to add INIT vectors for "
            "each of the cell in the cell pair, e.g. FIPNUM can be added as FIPNUM1 "
            "and FIPNUM2, and it is possible to filter to connections where f.ex "
            "FIPNUM change"
        ),
    )
    trans.fill_parser(trans_parser)
    trans_parser.set_defaults(func=trans.trans_main)

    pillars_parser = subparsers.add_parser(
        "pillars",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Compute data pr. cornerpoint pillar",
        description=(
            "Compute statistics pr. pillar in a cornerpoint grid, "
            "or alternatively by region parameter. Volumetrics, in-place, "
            "and contacts."
        ),
    )
    pillars.fill_parser(pillars_parser)
    pillars_parser.set_defaults(func=pillars.pillars_main)

    pvt_parser = subparsers.add_parser(
        "pvt",
        help="Extract PVT data",
        description=(
            "Extract data for the PVT keywords in an Eclipse deck "
            "and merge all data into a single dataframe. "
            "Supported keywords are PVTO, PVDO, PVTG, PVDG, PVTW, "
            "ROCK and DENSITY. Gas phase pressure and oil phase "
            "pressure are both called PRESSURE in the resulting "
            "dataframe, similar for volume factors and viscosity. "
            "Deduce meaning for column names from the Eclipse manual. "
            "The column KEYWORD denotes which PVT keyword a particular "
            "data row stems from. "
        ),
    )
    pvt.fill_parser(pvt_parser)
    pvt_parser.set_defaults(func=pvt.pvt_main)

    rft_parser = subparsers.add_parser(
        "rft",
        help=("Extract RFT data from Eclipse binary output files."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
    rft_parser.set_defaults(func=rft.rft_main)

    fipreports_parser = subparsers.add_parser(
        "fipreports",
        help=("Extract FIPxxxxx REPORT REGION data from Eclipse PRT output file."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Extract FIPxxxxx REPORT REGION data from PRT file. "
            "This parses currently in-place, outflows to wells and regions, and "
            "material balance errors"
        ),
    )
    fipreports.fill_parser(fipreports_parser)
    fipreports_parser.set_defaults(func=fipreports.fipreports_main)

    # Eclipse input files:
    satfunc_parser = subparsers.add_parser(
        "satfunc",
        help="Extract SWOF/SGOF/etc data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Data for all saturation functions are merged "
            "into one dataframe for all SATNUMs. Each row has data for a "
            "saturation point. For SWOF data, all columns related to SGOF "
            "are empty and vice versa"
        ),
    )

    satfunc.fill_parser(satfunc_parser)
    satfunc_parser.set_defaults(func=satfunc.satfunc_main)

    compdat_parser = subparsers.add_parser(
        "compdat",
        help="Extract COMPDAT data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Each row represents a cell connection to a well. "
            "Only COMPDAT data is exposed in CSV output currently."
        ),
    )
    compdat.fill_parser(compdat_parser)
    compdat_parser.set_defaults(func=compdat.compdat_main)

    equil_parser = subparsers.add_parser(
        "equil",
        help="Extract EQUIL data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=("Each row contains the equilibriation data for one EQLNUM."),
    )
    equil.fill_parser(equil_parser)
    equil_parser.set_defaults(func=equil.equil_main)

    gruptree_parser = subparsers.add_parser(
        "gruptree",
        help="Extract GRUPTREE data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=("Each row represents an edge in the GRUPTREE at a specific date."),
    )
    gruptree.fill_parser(gruptree_parser)
    gruptree_parser.set_defaults(func=gruptree.gruptree_main)

    wcon_parser = subparsers.add_parser(
        "wcon",
        help="Extract well control data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Each row represents the control data for a certain "
            "well or well wildcard at a specific date"
        ),
    )
    wcon.fill_parser(wcon_parser)
    wcon_parser.set_defaults(func=wcon.wcon_main)

    return parser


def main():
    """Entry point"""
    parser = get_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
