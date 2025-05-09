"""Module to hold simulator input and output filenames"""

import errno
import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

try:
    import opm.io

    HAVE_OPM = True
except ImportError:
    HAVE_OPM = False

from resdata.grid import Grid
from resdata.rd_util import FileMode
from resdata.resfile import ResdataFile
from resdata.summary import Summary

from .common import convert_lyrlist_to_zonemap, parse_lyrfile

logger = logging.getLogger(__name__)

if HAVE_OPM:
    # Default parse option to opm.io for a very permissive parsing
    OPMIOPARSER_RECOVERY: List[Tuple[str, Any]] = [
        ("PARSE_EXTRA_DATA", opm.io.action.ignore),
        ("PARSE_EXTRA_RECORDS", opm.io.action.ignore),
        ("PARSE_INVALID_KEYWORD_COMBINATION", opm.io.action.ignore),
        ("PARSE_MISSING_DIMS_KEYWORD", opm.io.action.ignore),
        ("PARSE_MISSING_INCLUDE", opm.io.action.ignore),
        ("PARSE_MISSING_SECTIONS", opm.io.action.ignore),
        ("PARSE_RANDOM_SLASH", opm.io.action.ignore),
        ("PARSE_RANDOM_TEXT", opm.io.action.ignore),
        ("PARSE_UNKNOWN_KEYWORD", opm.io.action.ignore),
        ("SUMMARY_UNKNOWN_GROUP", opm.io.action.ignore),
        ("UNSUPPORTED_*", opm.io.action.ignore),
    ]


class ResdataFiles(object):
    """
    Class for holding reservoir simulator :term:`output files <output file>`

    Exists only for convenience, so that loading of
    ResdataFile/Summary objects is easy for users, and with
    caching if wanted.

    Various functions that needs some of the simulator :term:`output <output file>`
    (or :term:`include file`) should be able to ask this class, and
    it should be loaded or served from cache.
    """

    def __init__(self, eclbase):
        # eclbase might be a a Posix path object
        eclbase = str(eclbase)

        # Hint about possible wrong filenames:
        if ".DATA" in eclbase and not Path(eclbase).is_file():
            logger.warning("File %s does not exist", eclbase)
            # (this is not an error, because it is possible
            # to obtain summary without the .DATA file being present)

        # Strip .DATA or . at end of eclbase:
        eclbase = rreplace(".DATA", "", eclbase)
        eclbase = rreplace(".", "", eclbase)
        self._eclbase = eclbase

        # Set class variables to None
        self._egridfile = None  # Should be ResdataFile
        self._initfile = None  # Should be ResdataFile
        self._summary = None  # Should be Summary

        self._egrid = None  # Should be Grid

        self._rstfile = None  # ResdataFile
        self._rftfile = None  # ResdataFile

        self._deck = None

    def get_path(self) -> Path:
        """Return the full path to the directory with the .DATA file"""
        return Path(self._eclbase).absolute().parent

    def get_deck(self) -> "opm.libopmcommon_python.Deck":
        """Return a opm.io :term:`deck` of the .DATA file"""
        if not self._deck:
            if Path(self._eclbase + ".DATA").is_file():
                deckfile = self._eclbase + ".DATA"
            else:
                deckfile = self._eclbase  # Will be any filename
            logger.info("Parsing deck file %s...", deckfile)
            parsecontext = opm.io.ParseContext(OPMIOPARSER_RECOVERY)
            deck = opm.io.Parser().parse(deckfile, parsecontext)
            self._deck = deck
        return self._deck

    @staticmethod
    def str2deck(
        string: str, parsecontext: Optional[List[Tuple[str, Any]]] = None
    ) -> "opm.libopmcommon_python.Deck":
        """Produce a opm.io :term:`deck` from a string, using permissive
        parsing by default"""
        if parsecontext is None:
            parsecontext = opm.io.ParseContext(OPMIOPARSER_RECOVERY)
        return opm.io.Parser().parse_string(string, parsecontext)

    @staticmethod
    def file2deck(filename: Union[str, Path]) -> "opm.libopmcommon_python.Deck":
        """Try to convert standalone files into opm.io Deck objects"""
        return ResdataFiles.str2deck(Path(filename).read_text(encoding="utf-8"))

    def get_egrid(self) -> Grid:
        """Find and return EGRID file as a Grid object"""
        if not self._egrid:
            egridfilename = self._eclbase + ".EGRID"
            if not Path(egridfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
            logger.info("Opening grid data from EGRID file: %s", egridfilename)
            self._egrid = Grid(egridfilename)
        return self._egrid

    def get_egridfile(self) -> ResdataFile:
        """Find and return the EGRID file as a ResdataFile object

        This gives access to data vectors defined on the grid."""
        if not self._egridfile:
            egridfilename = self._eclbase + ".EGRID"
            if not Path(egridfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
            logger.info("Opening data vectors from EGRID file: %s", egridfilename)
            self._egridfile = ResdataFile(egridfilename, flags=FileMode.CLOSE_STREAM)

        return self._egridfile

    def get_summary(self, include_restart: bool = True) -> Summary:
        """Find and return the summary file and
        return as Summary object

        Args:
            include_restart: Sent to resdata for whether restart files
                should be traversed.
        """
        if not self._summary:
            smryfilename = self._eclbase + ".UNSMRY"
            if not Path(smryfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), smryfilename
                )
            logger.info("Opening UNSMRY file: %s", smryfilename)
            self._summary = Summary(smryfilename, include_restart=include_restart)
        return self._summary

    def get_initfile(self) -> ResdataFile:
        """Find and return the INIT file as a ResdataFile object"""
        if not self._initfile:
            initfilename = self._eclbase + ".INIT"
            if not Path(initfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), initfilename
                )
            logger.info("Opening INIT file: %s", initfilename)
            self._initfile = ResdataFile(initfilename, flags=FileMode.CLOSE_STREAM)
        return self._initfile

    def get_rftfile(self) -> ResdataFile:
        """Find and return the RFT file as a ResdataFile object"""
        if not self._rftfile:
            rftfilename = self._eclbase + ".RFT"
            if not Path(rftfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rftfilename
                )
            logger.info("Opening RFT file: %s", rftfilename)
            self._rftfile = ResdataFile(rftfilename, flags=FileMode.CLOSE_STREAM)
        return self._rftfile

    def get_rstfile(self) -> ResdataFile:
        """Find and return the UNRST file as a ResdataFile object"""
        if not self._rstfile:
            rstfilename = self._eclbase + ".UNRST"
            if not Path(rstfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rstfilename
                )
            logger.info("Opening RST file: %s", rstfilename)
            self._rstfile = ResdataFile(rstfilename, flags=FileMode.CLOSE_STREAM)
        return self._rstfile

    def get_rstfilename(self) -> str:
        """Return the inferred name of the UNRST file"""
        return self._eclbase + ".UNRST"

    def get_prtfilename(self) -> str:
        """Return the inferred name of the PRT file"""
        return self._eclbase + ".PRT"

    def close(self) -> None:
        """Close any opened files. Most files are opened though ecl with
        an option to close the stream as possible, leaving not much work
        for this function."""
        self._egridfile = None
        self._initfile = None
        # This is necessary for garbage collection to close the Summary file:
        self._summary = None
        self._rstfile = None
        self._rftfile = None

    def get_zonemap(self, filename=None):
        """Return a dictionary from (int) K layers in the simgrid to strings

        Typical usage is to map from grid layer to zone names.

        The layer filename must currently follow format::

          'ZoneA' 1-4
          'ZoneB' 5-10

        where the single quotes are optional for zones without spaces.
        Write single layer zones as 11-11. NB: ResInsight requires single
        quotes always.

        Args:
            filename (str): Name of file. If relative path, relative to DATA
                file location. If nonexisting file, an empty dict will be
                returned and a warning issued.

        Returns:
            dict, integer keys which are the K layers. Every layer mentioned
                in the interval in the input file is present. Can be empty.
        """
        if not filename:
            filename_defaulted = True
            filename = "zones.lyr"
        else:
            filename_defaulted = False
        assert isinstance(filename, str)
        if not Path(filename).is_absolute():
            fullpath = Path(self.get_path()) / filename
        else:
            fullpath = filename
        if not Path(fullpath).is_file():
            if filename_defaulted:
                # No warnings when the default filename is not there.
                return {}
            logger.warning("Zonefile %s not found, ignoring", fullpath)
            return {}
        lyrlist = parse_lyrfile(fullpath)
        return convert_lyrlist_to_zonemap(lyrlist)


def rreplace(pat: str, sub: str, string: str) -> str:
    """Variant of str.replace() that only replaces at the end of the string"""
    return string[0 : -len(pat)] + sub if string.endswith(pat) else string  # noqa
