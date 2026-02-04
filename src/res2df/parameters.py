"""Support module for extra files with key-value information
related to simulator runs"""

import json
import logging
import warnings
from pathlib import Path
from typing import Any, cast

import pandas as pd
import yaml

from .resdatafiles import ResdataFiles

logger = logging.getLogger(__name__)


def find_parameter_files(
    deckpath: ResdataFiles | str | Path, filebase: str = "parameters"
) -> list[Path]:
    """Locate a default prioritized list of files to try to read as key-value

    File extensions .yml, .json and .txt are recognized and will be found in
    current dir, one directory up, and two directories up.

    Args:
        deckpath: Either a ResdataFiles object of
            a simulator output set (only the corresponding path will be used),
            or path to a file or directory, that will be used as a starting
            point for locating parameter files
        filebase: the base of filenames to look for.

    Return:
        Absolute paths to filenames. Empty list if nothing found
    """
    eclbasepath: Path
    fname: str
    if isinstance(deckpath, ResdataFiles):
        eclbasepath = Path(deckpath.get_path())
    elif isinstance(deckpath, (str, Path)):
        eclbasepath = Path(deckpath).parent.absolute()
    else:
        raise TypeError
    files_to_lookfor: list[str] = [
        filebase + ".json",
        filebase + ".yml",
        filebase + ".txt",
        filebase,
    ]
    paths_to_check: list[Path] = [Path(), Path(".."), Path("..") / Path("..")]
    foundfiles = []
    for path in paths_to_check:
        for fname in files_to_lookfor:
            fullfname = eclbasepath / path / Path(fname)
            if fullfname.is_file():
                foundfiles.append(fullfname.resolve())
    return foundfiles


def load_parameterstxt(filename: str | Path) -> dict[str, Any]:
    """Read parameters.txt into a dictionary

    Lines starting with a hash will be ignored.

    Args:
        filename: file containing one key-value pair pr. line,
            separated by whitespace
    """
    with warnings.catch_warnings(record=True):
        # From pandas 1.4, too many columns result in a ParserWarning for dropped
        # data. This is risky, and therefore catching the warning and raising a
        # ParserError instead.
        warnings.filterwarnings("error")
        try:
            dframe = pd.read_csv(
                filename,
                comment="#",
                sep=r"\s",
                engine="python",
                names=["KEY", "VALUE"],
                index_col=False,
                dtype={"KEY": str},
            )
        except pd.errors.ParserWarning as txt_exc:
            raise pd.errors.ParserError(txt_exc) from txt_exc

    return cast(dict[str, Any], dframe.set_index("KEY")["VALUE"].to_dict())


def load_all(
    filenames: list[str] | list[Path], warnduplicates: bool = True
) -> dict[str, Any]:
    """Reads a list of parameter filenames

    Dictionaries for all files will be merged into one.

    Keys must be unique over all filenames, if not
    only the first occurence will be used (based on
    the order of filenames).

    Args:
        filenames: Order matters.
        warnduplicates: If True (default), overlapping keys will be warned.
    """
    keyvalues: dict[str, Any] = {}
    for fname in filenames:
        new_params = load(fname)
        if warnduplicates and keyvalues:
            duplicates = set(keyvalues.keys()).intersection(set(new_params.keys()))
            if duplicates:
                logger.debug("Duplicates keys %s", duplicates)
        new_params.update(keyvalues)
        keyvalues = new_params
    return keyvalues


def load(filename: str | Path) -> dict[str, Any]:
    """Read a parameter file as txt, yaml or json

    Returns:
        dict() with parameter names as keys. Empty dictionary if
            no parameters in the file.

    Raises ValueError or IOError if no files are readable
    """
    params_dict = None

    if not Path(filename).is_file():
        raise FileNotFoundError(str(filename) + " not found")
    file_content = Path(filename).read_text(encoding="utf-8")
    if not file_content.strip():
        logger.warning("%s was empty", filename)
        return {}

    yaml_error = ""
    try:
        logger.debug("Trying to parse %s with yaml.safe_load()", filename)
        params_dict = yaml.safe_load(file_content)
        logger.debug(" - ok, parsed as yaml")
        if not isinstance(params_dict, dict):
            # yaml happily parses txt files into a single line, don't want that.
            params_dict = None
    except yaml.YAMLError as yaml_exc:
        yaml_error = str(yaml_exc)
        logger.debug("%s was not parseable with yaml, trying json.", filename)

    json_error = ""
    if params_dict is None:
        try:
            logger.debug("Trying to parse %s with json.load()", filename)
            params_dict = json.loads(file_content)
            if not isinstance(params_dict, dict):
                params_dict = None
            logger.debug(" - ok, parsed as json")
        except json.JSONDecodeError as json_exc:
            json_error = str(json_exc)
            logger.debug("%s was not parseable with json, trying txt.", filename)

    txt_error = ""
    if params_dict is None:
        try:
            logger.debug("Trying to parse %s as txt with pd.read_csv()", filename)
            params_dict = load_parameterstxt(filename)
            if not isinstance(params_dict, dict):
                params_dict = None
            logger.debug(" - ok, parsed as txt")
        except (pd.errors.ParserError, ValueError) as txt_exc:
            txt_error = str(txt_exc)
            logger.debug("%s was not parseable as txt, no more options", filename)

    if params_dict is None:
        logger.warning("%s could not be parsed as yaml, json or txt", filename)
        logger.warning("%s%s%s", yaml_error, json_error, txt_error)
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
