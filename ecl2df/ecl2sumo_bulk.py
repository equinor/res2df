import logging
from pathlib import Path
import importlib
from inspect import signature, Parameter
from typing import List
from fmu.config.utilities import yaml_load

logger = logging.getLogger(__name__)


standard_options = {
    "initvectors": None,  # List[str]
    "keywords": None,  # List[str] x3
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
    "end_date": "",  # str
    "params": False,  # bool
    "paramfile": None,  # str
    "include_restart": False,  # bool
}


def bulk_upload(eclpath, config_path, include: List = None, options: dict = None):
    """Bulk uploads every module to sumo with metadata

    eclpath (str): path to eclipse datafile
    config_path (str): path to fmu config file
    include (List): list of submodules to include. Defaults to None which includes all
    """
    if options is None:
        options = standard_options

    submod_list = [
        "compdat",
        "equil",
        "faults",
        "fipreports",
        "grid",
        "nnc",
        "pillars",
        "pvt",
        "rft",
        "satfunc",
        "summary",
    ]

    for submod_name in submod_list:
        if include is None or submod_name in include:
            func = importlib.import_module("ecl2df." + submod_name).export_w_metadata
            sig_items = signature(func).parameters.items()
            filtered_options = {
                name: options[name]
                for name, param in sig_items
                if param.kind is not Parameter.empty
                and name not in {"eclpath", "config_path"}
            }
            func(eclpath, config_path, **filtered_options)
            # break


def glob_for_datafiles(path="eclipse/model/"):
    return Path(path).glob("*.DATA")


def bulk_upload_with_configfile(config_path):
    """Export eclipse results controlled by config file

    Args:
        config_path (str): path to config file
    """
    config = yaml_load(config_path)
    try:
        ecl_config = config["ecl2csv"]
        try:
            eclpaths = ["eclipse/model/" + ecl_config["datafile"]]
            includes = ecl_config.get("datatypes", None)
            options = ecl_config.get("options", None)

        except (KeyError, AttributeError, TypeError):
            eclpaths = glob_for_datafiles()
            includes = None
            options = None

        for name in ["access", "masterdata", "model"]:
            print(config[name])

        for eclpath in eclpaths:
            bulk_upload(str(eclpath), config_path, includes, options)

    except KeyError:
        logger.warning("No eclipse export set up, you will not get anything exported")
