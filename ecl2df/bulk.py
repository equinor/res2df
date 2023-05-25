import sys
import logging
import argparse
from pathlib import Path
import importlib
from inspect import signature, Parameter
from typing import List
from fmu.config.utilities import yaml_load
from ecl2df.constants import SUBMODULES

logger = logging.getLogger(__name__)


standard_options = {
    "initvectors": None,  # List[str]
    "keywords": None,  # List[str] x3
    "keyword": "VFPPROD",
    "vfpnumbers": "",
    "fipname": "FIPNUM",  # str
    "vectors": "*",  # List[str]
    "stackdates": False,  # bool x2
    "dropconstants": False,  # bool
    "arrow": False,  # bool x2
    "coords": False,  # bool
    "pillars": False,  # bool
    "region": "",  # str
    "rstdates": "",  # str
    "soilcutoff": 0.5,  # float
    "sgascutoff": 0.5,  # float
    "swatcutoff": 0.5,  # float
    "group": False,  # bool
    "wellname": None,  # str
    "date": None,  # str
    "time_index": "raw",  # str
    "column_keys": None,
    "start_date": "",  # str
    "startdate": None,
    "end_date": "",  # str
    "params": False,  # bool
    "paramfile": None,  # str
    "include_restart": False,  # bool
    "boundaryfilter": False,
    "onlyk": False,
    "onlyij": False,
    "nnc": False,
    "verbose": False,
    "zonemap": "tut",
    "use_wellconnstatus": False,
    "excl_well_startswith": None,
}


def fill_parser(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Set up sys.argv parsers.

    Arguments:
        parser (argparse.ArgumentParser or argparse.subparser): parser to
            fill with arguments
    """
    # parser.add_argument("DATAFILE", help="Name of Eclipse DATA file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Be verbose")
    return parser


def bulk_export(eclpath, config_path, include: List = None, options: dict = None):
    """Bulk uploads every module to sumo with metadata

    eclpath (str): path to eclipse datafile
    config_path (str): path to fmu config file
    include (List): list of submodules to include. Defaults to None which includes all
    """
    # Substituting the options passed in into standard options
    if options is not None:
        for key, value in options.items():
            if key in standard_options:
                standard_options[key] = value
    logger.info("Running bulk export with options: %s", options)
    if include is None:
        include = SUBMODULES
    for submod_name in include:
        if submod_name in include:
            func = importlib.import_module("ecl2df." + submod_name).export_w_metadata
            sig_items = signature(func).parameters.items()
            filtered_options = {
                name: standard_options[name]
                for name, param in sig_items
                if param.kind is not Parameter.empty
                and name not in {"eclpath", "config_path"}
            }
            try:
                func(eclpath, config_path, **filtered_options)
                logger.info("Export of %s data", submod_name)
            except Exception:
                _, exp_mess, _ = sys.exc_info()
                logger.warning(
                    "Exception :%s while exporting %s", exp_mess, submod_name
                )

        else:
            logger.warning("This is not included %s", submod_name)


def glob_for_datafiles(path="eclipse/model/"):
    """glob for data files in folder

    Args:
        path (str, optional): The folder for eclipse models.
                              Defaults to "eclipse/model/".

    Returns:
        generator: the generator made
    """
    return Path(path).glob("*.DATA")


def get_ecl2csv_setting(ecl_config, keyword):
    """Get value from ecl_config dict

    Args:
        ecl_config (dict, bool): dictionary of ecl2csv key, value pairs, or just bool
        keyword (str): key in dictionary

    Returns:
        str, value: _description_
    """
    logger.debug("fetching %s", keyword)
    setting = None
    try:
        setting = ecl_config.get(keyword, None)
    except AttributeError:
        logger.debug("ecl_config is bool.")
    logger.debug("Returning ecl setting %s", setting)
    return setting


def remove_numbers(string):
    """Remove digits at end of string

    Args:
        string (str): a string

    Returns:
        string: string without digit at end
    """
    logger.debug("Will remove numbers from %s", string)
    while string[-1].isdigit() or string.endswith("-"):
        string = string[:-1]
    return string


def bulk_export_with_configfile(config_path, eclpath=None):
    """Export eclipse results controlled by config file

    Args:
        config_path (str): path to config file
    """
    config = yaml_load(config_path)
    print(config["ecl2csv"])
    eclpaths = ()
    datatypes = None
    options = None
    ecl_config = {}
    try:
        ecl_config = config["ecl2csv"]
        print(ecl_config)
        datatypes = get_ecl2csv_setting(ecl_config, "datatypes")
        options = get_ecl2csv_setting(ecl_config, "options")

        if eclpath is not None:
            eclpath = Path(eclpath)
        else:
            eclpath = get_ecl2csv_setting(ecl_config, "datafile")
        logger.debug("eclpath: %s", eclpath)

        if eclpath is None:
            print("Have to look for the files")
            eclpaths = glob_for_datafiles()
        else:
            # The complexity of the glob below is to
            # deal with numbers not in ecl path
            eclpaths = list(
                list(
                    eclpath.parent.glob(
                        remove_numbers(eclpath.name.replace(eclpath.suffix, ""))
                        + "*.DATA"
                    )
                )
            )

        # print(list(eclpaths))
        logger.debug("datatypes: %s", datatypes)
        logger.debug("options: %s", options)
        logger.debug("datafiles %s", eclpaths)

    except KeyError:
        logger.warning("No export from ecl included in this setup")

    for eclpath in eclpaths:
        logger.info("Working with %s", eclpath)
        bulk_export(str(eclpath), config_path, datatypes, options)


def bulk_main(args):
    """Generate all datatypes

    Args:
        args (argparse.NameSpace): The input arguments
    """
    bulk_export_with_configfile(args.config_path)
