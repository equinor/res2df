"""Support module for extra files with key-value information
related to Eclipse runs"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd
import yaml

from ecl2df.eclfiles import EclFiles

logger = logging.getLogger(__name__)


def find_parameter_files(
    ecldeck_or_eclpath: Union[EclFiles, str, Path], filebase: str = "parameters"
) -> List[Path]:
    """Locate a default prioritized list of files to try to read as key-value

    File extensions .yml, .json and .txt are recognized and will be found in
    current dir, one directory up, and two directories up.

    Args:
        ecldeck_or_eclpath: Either an EclFiles object of
            an Eclipse output set (only the corresponding path will be used),
            or path to a file or directory, that will be used as a starting
            point for locating parameter files
        filebase: the base of filenames to look for.

    Return:
        Absolute paths to filenames. Empty list if nothing found
    """
    eclbasepath: Path
    fname: str
    if isinstance(ecldeck_or_eclpath, EclFiles):
        eclbasepath = Path(ecldeck_or_eclpath.get_path())
    elif isinstance(ecldeck_or_eclpath, (str, Path)):
        eclbasepath = Path(ecldeck_or_eclpath).parent.absolute()
    else:
        raise TypeError
    files_to_lookfor: List[str] = [
        filebase + ".json",
        filebase + ".yml",
        filebase + ".txt",
        filebase,
    ]
    paths_to_check: List[Path] = [Path("."), Path(".."), Path("..") / Path("..")]
    foundfiles = []
    for path in paths_to_check:
        for fname in files_to_lookfor:
            fullfname = eclbasepath / path / Path(fname)
            if fullfname.is_file():
                foundfiles.append(fullfname.resolve())
    return foundfiles


def load_parameterstxt(filename: Union[str, Path]) -> Dict[str, Any]:
    """Read parameters.txt into a dictionary

    Lines starting with a hash will be ignored.

    Args:
        filename: file containing one key-value pair pr. line,
            separated by whitespace
    """
    dframe = pd.read_csv(
        filename, comment="#", sep=r"\s", engine="python", names=["KEY", "VALUE"]
    )
    return dframe.set_index("KEY")["VALUE"].to_dict()


def load_all(
    filenames: Union[List[str], List[Path]], warnduplicates: bool = True
) -> Dict[str, Any]:
    """Reads a list of parameter filenames

    Dictionaries for all files will be merged into one.

    Keys must be unique over all filenames, if not
    only the first occurence will be used (based on
    the order of filenames).

    Args:
        filenames: Order matters.
        warnduplicates: If True (default), overlapping keys will be warned.
    """
    keyvalues: Dict[str, Any] = {}
    for fname in filenames:
        new_params = load(fname)
        if warnduplicates and keyvalues:
            duplicates = set(keyvalues.keys()).intersection(set(new_params.keys()))
            if duplicates:
                logger.debug("Duplicates keys %s", str(duplicates))
        new_params.update(keyvalues)
        keyvalues = new_params
    return keyvalues


def load(filename: Union[str, Path]) -> Dict[str, Any]:
    """Read a parameter file as txt, yaml or json

    Returns:
        dict() with parameter names as keys. Empty dictionary if
            no parameters in the file.

    Raises ValueError or IOError if no files are readable
    """
    params_dict = None

    if not Path(filename).exists():
        raise FileNotFoundError(str(filename) + " not found")

    if not Path(filename).read_text(encoding="utf-8").strip():
        logger.warning("%s was empty", filename)
        return {}

    yaml_error = ""
    try:
        logger.debug("Trying to parse %s with yaml.safe_load()", filename)
        params_dict = yaml.safe_load(Path(filename).read_text(encoding="utf-8"))
        logger.debug(" - ok, parsed as yaml")
        if not isinstance(params_dict, dict):
            # yaml happily parses txt files into a single line, don't want that.
            params_dict = None
    except Exception as yaml_exc:
        yaml_error = str(yaml_exc)
        logger.debug("%s was not parseable with yaml, trying json.", filename)

    json_error = ""
    if not params_dict:
        try:
            logger.debug("Trying to parse %s with json.load()", filename)
            with open(filename, encoding="utf-8") as f_handle:
                params_dict = json.load(f_handle)
            assert isinstance(params_dict, dict)
            logger.debug(" - ok, parsed as yaml")
        except Exception as json_exc:
            json_error = str(json_exc)
            logger.debug("%s was not parseable with json, trying txt.", filename)

    txt_error = ""
    if not params_dict:
        try:
            logger.debug("Trying to parse %s as txt with pd.read_csv()", filename)
            params_dict = load_parameterstxt(filename)
            assert isinstance(params_dict, dict)
            logger.debug(" - ok, parsed as txt")
        except Exception as txt_exc:
            txt_error = str(txt_exc)
            logger.debug("%s was not parseable as txt, no more options", filename)

    if not params_dict:
        logger.warning("%s could not be parsed as yaml, json or txt", filename)
        logger.warning("%s%s%s", str(yaml_error), str(json_error), str(txt_error))
        raise ValueError(f"Could not parse {filename}")

    # Filter to values that are NOT dict's. We can have dict as value when
    # "grouped" keys are present in the json files, both as "group:key value"
    # and in a dict called group
    params_dict = {
        key: value
        for (key, value) in params_dict.items()
        if not isinstance(value, dict)
    }
    return params_dict
