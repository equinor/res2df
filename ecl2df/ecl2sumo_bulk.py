from inspect import signature, Parameter
from typing import List
from ecl2df.compdat import export_w_metadata as compdat
from ecl2df.equil import export_w_metadata as equil
from ecl2df.faults import export_w_metadata as faults
from ecl2df.fipreports import export_w_metadata as fipreports
from ecl2df.grid import export_w_metadata as grid
from ecl2df.nnc import export_w_metadata as nnc
from ecl2df.pillars import export_w_metadata as pillars
from ecl2df.pvt import export_w_metadata as pvt
from ecl2df.rft import export_w_metadata as rft
from ecl2df.satfunc import export_w_metadata as satfunc
from ecl2df.summary import export_w_metadata as summary

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


def bulk_upload(eclpath, metadata_path, include: List = None, options=None):
    """Bulk uploads every module to sumo with metadata

    eclpath (str): path to eclipse datafile
    metadata_path (str): path to metadata file
    include (List): list of submodules to include. Defaults to None which includes all
    """
    if options is None:
        options = standard_options

    subfunc_list = [
        compdat,
        equil,
        faults,
        fipreports,
        grid,
        nnc,
        pillars,
        pvt,
        rft,
        satfunc,
        summary,
    ]

    for subfunc in subfunc_list:
        if include is None or subfunc.__name__ in include:
            sig_items = signature(subfunc).parameters.items()
            filtered_options = {
                name: options[name]
                for name, param in sig_items
                if param.kind is not Parameter.empty
                and name not in {"eclpath", "metadata_path"}
            }
            subfunc(eclpath, metadata_path, **filtered_options)
