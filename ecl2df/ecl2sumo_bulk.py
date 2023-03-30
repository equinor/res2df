import argparse
from typing import List
from ecl2df.compdat import compdat_main
from ecl2df.equil import equil_main
from ecl2df.faults import faults_main
from ecl2df.fipreports import fipreports_main
from ecl2df.grid import grid_main
from ecl2df.nnc import nnc_main
from ecl2df.pillars import pillars_main
from ecl2df.pvt import pvt_main
from ecl2df.rft import rft_main
from ecl2df.satfunc import satfunc_main
from ecl2df.summary import summary_main


def compdat(eclpath: str, metadata_path: str, initvectors: List[str] = None):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        fipname (str, optional): Region parameter name of interest, default: FIPNUM
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="compdat.csv",
        initvectors=initvectors,
    )
    compdat_main(args)


def equil(
    eclpath: str,
    metadata_path: str,
    keywords: List[str] = None,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        fipname (str, optional): Region parameter name of interest, default: FIPNUM
    """
    args = argparse.Namespace(
        DATAFILE=eclpath, metadata=metadata_path, output="equil.csv", keywords=keywords
    )
    equil_main(args)


def faults(
    eclpath: str,
    metadata_path: str,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        fipname (str, optional): Region parameter name of interest, default: FIPNUM
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="faults.csv",
    )
    faults_main(args)


def fipreports(
    eclpath: str,
    metadata_path: str,
    fipname: str = "FIPNUM",
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        fipname (str, optional): Region parameter name of interest, default: FIPNUM
    """
    args = argparse.Namespace(
        PRTFILE=eclpath,
        metadata=metadata_path,
        output="fipreports.csv",
        fipname=fipname,
    )
    fipreports_main(args)


def grid(
    eclpath: str,
    metadata_path: str,
    vectors: List[str] = "*",
    rstdates: str = "",
    stackdates: bool = False,
    dropconstants: bool = False,
    arrow: bool = False,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        region (str): region parameter to separate by, empty string give no sep
        rstdates (str): Point in time to grab restart data from,
                either 'first' or 'last', 'all' or a date in YYYY-MM-DD format
        stackdates (bool, optional): default False
        dropconstants (bool, optional):Drop constant columns from the dataset, default False
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="grid.csv",
        vectors=vectors,
        rstdates=rstdates,
        stackdates=stackdates,
        dropconstants=dropconstants,
        arrow=arrow,
    )
    grid_main(args)


def nnc(
    eclpath: str,
    metadata_path: str,
    coords: bool = False,
    pillars: bool = False,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        coords (bool, optional): Add xyz coords of connection midpoint, default False
        pillars (bool, optional): Only dump vertical (along pillars) connections, default False
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="nnc.csv",
        coords=coords,
        pillars=pillars,
    )
    nnc_main(args)


def pillars(
    eclpath: str,
    metadata_path: str,
    region: str = "",
    rstdates: str = "",
    stackdates: bool = False,
    soilcutoff: float = 0.5,
    sgascutoff: float = 0.5,
    swatcutoff: float = 0.5,
    group: bool = False,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        region (str): region parameter to separate by, empty string give no sep
        rstdates (str): Point in time to grab restart data from,
                either 'first' or 'last', 'all' or a date in YYYY-MM-DD format
        stackdates (bool): ,
        soilcutoff (float): default 0.5
        sgascutoff (float): default 0.5,
        swatcutoff: (float): default 0.5,
        group (bool): default False,
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="pillars.csv",
        region=region,
        rstdates=rstdates,
        stackdates=stackdates,
        soilcutoff=soilcutoff,
        sgascutoff=sgascutoff,
        swatcutoff=swatcutoff,
        group=group,
    )
    pillars_main(args)


def pvt(
    eclpath: str,
    metadata_path: str,
    keywords: List = None,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        keywords (list): list of keywords to include, None gives all, default None
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="pvt.csv",
        keywords=keywords,
    )
    pvt_main(args)


def rft(
    eclpath: str,
    metadata_path: str,
    wellname: str = None,
    date: str = None,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        wellname (str): restrict to one well, None gives all, default None
        date (str): restrict to one date, None gives all, format is iso  8601 YYYY-MM-DD, default None
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        wellname=wellname,
        date=date,
        output="rft.csv",
    )
    rft_main(args)


def satfunc(
    eclpath: str,
    metadata_path: str,
    keywords: List = None,
):
    """Read satfunc data from disk, write csv back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        keywords (list): list of keywords to include, None gives all, default None
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="satfunc.csv",
        keywords=keywords,
    )
    satfunc_main(args)


def summary(
    eclpath: str,
    metadata_path: str,
    time_index="raw",
    column_keys=None,
    start_date="",
    end_date="",
    params=False,
    paramfile=None,
    arrow=False,
    include_restart=False,
):
    """Read summary data from disk, write csv/arrow back to disk with metadata

    Args:
        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        time_index (str, optional): define what sampling for time index, raw is no resampling. Defaults to "raw".
        column_keys (_type_, optional): What columns to extract, use summary column wildcards, None means all. Defaults to None.
        start_date (str, optional): From when index should start. Defaults to "".
        end_date (str, optional): From when time index should end. Defaults to "".
        params (bool, optional): inlclude parameters from ert run. Defaults to False.
        paramfile (str, optional): path to parameter file. Defaults to None.
        arrow (bool, optional): write arrow file, not csv. Defaults to False.
        include_restart (bool, optional): Attempt to include data before restart. Defaults to False.
    """
    args = argparse.Namespace(
        DATAFILE=eclpath,
        metadata=metadata_path,
        output="summary.csv",
        time_index=time_index,
        column_keys=column_keys,
        start_date=start_date,
        end_date=end_date,
        params=params,
        paramfile=paramfile,
        arrow=arrow,
        include_restart=include_restart,
    )
    summary_main(args)


def bulk_upload(eclpath, metadata_path, include:List = None):
    """Bulk uploads every module to sumo with metadata

        eclpath (str): path to eclipse datafile
        metadata_path (str): path to metadata file
        include (List): list of submodules to include. Defaults to None which includes all
    """
    subfunc_list = [compdat, equil, faults, fipreports, grid, nnc, pvt, rft, satfunc, summary]

    for subfunc in subfunc_list:
        if include is None or subfunc.__name__ in include:
            subfunc(eclpath, metadata_path)
