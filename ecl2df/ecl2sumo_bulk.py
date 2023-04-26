import importlib
from inspect import signature, Parameter
from typing import List


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


# def bulk_upload_with_configfile(eclpath, config_path):
