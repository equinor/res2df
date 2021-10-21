#!/usr/bin/env python
"""
End-user command line tool for accessing functionality
in ecl2df
"""
import argparse
import functools
import importlib
import sys
from typing import Optional

from ecl2df import __version__

# String constants in use for generating ERT forward model documentation:
DESCRIPTION: str = """Convert Eclipse input and output files into CSV files,
with the command line utility ``ecl2csv``. Run ``ecl2csv --help`` to see
which subcommands are supported.

For supplying options to subcommands, you can use the arguments ``<XARGn>``
where ``n`` goes from 1 to 10.

For more documentation, see https://equinor.github.io/ecl2df/.
"""
CATEGORY: str = "utility.eclipse"
EXAMPLES: str = """

Outputting the EQUIL data from an Eclipse deck. The ECLBASE variable from your
ERT config is supplied implicitly::

   FORWARD_MODEL ECL2CSV(<SUBCOMMAND>=equil, <OUTPUT>=equil.csv)

For a yearly summary export of the realization, options have to be supplied
with the XARG options::

  FORWARD_MODEL ECL2CSV(<SUBCOMMAND>=summary, <OUTPUT>=yearly.csv, <XARG1>="--time_index", <XARG2>="yearly")

The quotes around double-dashed options are critical to avoid ERT taking for a
comment. For more options, use ``<XARG3>`` etc.
"""  # noqa


def get_parser() -> argparse.ArgumentParser:
    """Make parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "ecl2csv (" + __version__ + ") is a command line frontend to ecl2df. "
            "Documentation at https://equinor.github.io/ecl2df/ "
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    if sys.version_info.major >= 3 and sys.version_info.minor >= 7:
        subparsers = parser.add_subparsers(  # type: ignore
            required=True,
            dest="subcommand",
            parser_class=argparse.ArgumentParser,
        )
    else:
        subparsers = parser.add_subparsers(parser_class=argparse.ArgumentParser)

    subparsers_dict = {}
    subparsers_dict["grid"] = subparsers.add_parser(
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
    subparsers_dict["summary"] = subparsers.add_parser(
        "summary",
        help=("Extract summary data"),
        description=(
            "This is the time-dependent data for "
            "field production data, well profiles etc. Each row contains data "
            "for one point in time"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers_dict["nnc"] = subparsers.add_parser(
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
    subparsers_dict["faults"] = subparsers.add_parser(
        "faults",
        help="Extract data from the FAULTS keyword",
        description=(
            "Each row represents a particular cell and a face and the name of the fault"
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers_dict["trans"] = subparsers.add_parser(
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
    subparsers_dict["pillars"] = subparsers.add_parser(
        "pillars",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help="Compute data pr. cornerpoint pillar",
        description=(
            "Compute statistics pr. pillar in a cornerpoint grid, "
            "or alternatively by region parameter. Volumetrics, in-place, "
            "and contacts."
        ),
    )
    subparsers_dict["pvt"] = subparsers.add_parser(
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
    subparsers_dict["rft"] = subparsers.add_parser(
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
    subparsers_dict["fipreports"] = subparsers.add_parser(
        "fipreports",
        help=("Extract FIPxxxxx REPORT REGION data from Eclipse PRT output file."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Extract FIPxxxxx REPORT REGION data from PRT file. "
            "This parses currently in-place, outflows to wells and regions, and "
            "material balance errors"
        ),
    )
    subparsers_dict["satfunc"] = subparsers.add_parser(
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
    subparsers_dict["fipreports"] = subparsers.add_parser(
        "fipreports",
        help=("Extract FIPxxxxx REPORT REGION data from Eclipse PRT output file."),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Extract FIPxxxxx REPORT REGION data from PRT file. "
            "This parses currently in-place, outflows to wells and regions, and "
            "material balance errors"
        ),
    )
    subparsers_dict["compdat"] = subparsers.add_parser(
        "compdat",
        help="Extract COMPDAT data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Each row represents a cell connection to a well. "
            "Only COMPDAT data is exposed in CSV output currently."
        ),
    )
    subparsers_dict["equil"] = subparsers.add_parser(
        "equil",
        help="Extract EQUIL data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=("Each row contains the equilibriation data for one EQLNUM."),
    )
    subparsers_dict["gruptree"] = subparsers.add_parser(
        "gruptree",
        help="Extract GRUPTREE data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=("Each row represents an edge in the GRUPTREE at a specific date."),
    )
    subparsers_dict["wellconnstatus"] = subparsers.add_parser(
        "wellconnstatus",
        help="Extract well connection status",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Each row represents an event where a well connection is changing status."
        ),
    )
    subparsers_dict["wcon"] = subparsers.add_parser(
        "wcon",
        help="Extract well control data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Each row represents the control data for a certain "
            "well or well wildcard at a specific date"
        ),
    )

    for submodule, subparser in subparsers_dict.items():
        # Use the submodule's fill_parser() to add the submodule specific
        # arguments:
        importlib.import_module("ecl2df." + submodule).fill_parser(  # type: ignore
            subparser
        )

        # Add empty placeholders, this looks strange but is needed for the
        # ERT forward model frontend, where non-used options must be supplied
        # as empty string arguments (which we should ignore)
        subparser.add_argument(
            "hiddenemptyplaceholders", nargs="*", help=argparse.SUPPRESS
        )

        # Tell argparse which main() function to use for each
        # subparser/submodule:
        subparser.set_defaults(
            func=functools.partial(
                run_subparser_main, submodule=submodule, parser=subparser
            )
        )

    return parser


def run_subparser_main(
    args,
    submodule: str,
    parser: Optional[argparse.ArgumentParser] = None,
) -> None:
    """Wrapper for running the subparsers main() function, with
    custom argument handling.

    In order to support ERT forward model syntax, empty positional
    arguments must be allowed, but ignored. This function takes
    care of shuffling the single required positional argument into
    args.DATAFILE, and will error if more than one positional
    argument is supplied

    This function is to be supplied to argsparse's set_default()
    function, by use of functools.partial so that the submodule_name
    argument can be set.

    Args:
        args (Namespace): argparse argument namespace
        submodule: One of ecl2df's submodules. That module
            must have a function called <submodule>_main()
        parser: Used for raising errors.
    """
    if "DATAFILE" in args:
        positionals = list(filter(len, [args.DATAFILE] + args.hiddenemptyplaceholders))
        args.DATAFILE = "".join([args.DATAFILE] + args.hiddenemptyplaceholders)
    elif "PRTFILE" in args:
        # Special treatment for the fipreports submodule
        positionals = list(filter(len, [args.PRTFILE] + args.hiddenemptyplaceholders))
        args.PRTFILE = "".join([args.PRTFILE] + args.hiddenemptyplaceholders)
    if len(positionals) > 1 and parser is not None:
        parser.error(f"Unknown argument in {positionals}")

    mod = importlib.import_module("ecl2df." + submodule)

    main_func = getattr(mod, submodule + "_main")
    main_func(args)


def main() -> None:
    """Entry point"""
    parser = get_parser()
    args = parser.parse_args()
    if "arrow" in parser.prog:
        args.__dict__["arrow"] = True
    args.func(args)


if __name__ == "__main__":
    main()
