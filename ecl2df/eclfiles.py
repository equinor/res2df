"""
Module to hold Eclipse input and output filenames
"""

import os
import errno
import logging
import shlex
from pathlib import Path

import opm.io

from ecl.eclfile import EclFile
from ecl.grid import EclGrid
from ecl.summary import EclSum

logger = logging.getLogger(__name__)

# Default parse option to opm.io for a very permissive parsing
OPMIOPARSER_RECOVERY = [
    ("PARSE_UNKNOWN_KEYWORD", opm.io.action.ignore),
    ("SUMMARY_UNKNOWN_GROUP", opm.io.action.ignore),
    ("PARSE_RANDOM_SLASH", opm.io.action.ignore),
    ("UNSUPPORTED_*", opm.io.action.ignore),
    ("PARSE_MISSING_SECTIONS", opm.io.action.ignore),
    ("PARSE_MISSING_DIMS_KEYWORD", opm.io.action.ignore),
    ("PARSE_RANDOM_TEXT", opm.io.action.ignore),
    ("PARSE_MISSING_INCLUDE", opm.io.action.ignore),
    ("PARSE_EXTRA_RECORDS", opm.io.action.ignore),
    ("PARSE_EXTRA_DATA", opm.io.action.ignore),
]


class EclFiles(object):
    """
    Class for holding an Eclipse deck with result files

    Exists only for convenience, so that loading of
    EclFile/EclSum objects is easy for users, and with
    caching if wanted.

    Various functions that needs some of the Eclipse output
    (or input file) should be able to ask this class, and
    it should be loaded or served from cache.
    """

    def __init__(self, eclbase):
        # eclbase might be a a Posix path object
        eclbase = str(eclbase)

        # Hint about possible wrong filenames:
        if ".DATA" in eclbase and not Path(eclbase).is_file():
            logger.warning("File %s does not exist", eclbase)
            # (this is not an error, because it is possible
            # to obtain summary without the DATA file being present)

        # Strip .DATA or . at end of eclbase:
        eclbase = rreplace(".DATA", "", eclbase)
        eclbase = rreplace(".", "", eclbase)
        self._eclbase = eclbase

        # Set class variables to None
        self._egridfile = None  # Should be EclFile
        self._initfile = None  # Should be EclFile
        self._eclsum = None  # Should be EclSum

        self._egrid = None  # Should be EclGrid

        self._rstfile = None  # EclFile
        self._rftfile = None  # EclFile

        self._deck = None

    def get_path(self):
        """Return the full path to the directory with the DATA file"""
        return Path(self._eclbase).absolute().parent

    def get_ecldeck(self):
        """Return a opm.io deck of the DATA file"""
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
    def str2deck(string, parsecontext=None):
        """Produce a opm.io deck from a string, using permissive
        parsing by default"""
        if not parsecontext:
            parsecontext = opm.io.ParseContext(OPMIOPARSER_RECOVERY)
        return opm.io.Parser().parse_string(string, parsecontext)

    @staticmethod
    def file2deck(filename):
        """Try to convert standalone files into opm.io Deck objects"""
        with open(filename) as fhandle:
            filestring = "".join(fhandle.readlines())
            return EclFiles.str2deck(filestring)

    def get_egrid(self):
        """Find and return EGRID file as an EclGrid object"""
        if not self._egrid:
            egridfilename = self._eclbase + ".EGRID"
            if not Path(egridfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
            logger.info("Opening grid data from EGRID file: %s", egridfilename)
            self._egrid = EclGrid(egridfilename)
        return self._egrid

    def get_egridfile(self):
        """Find and return the EGRID file as a EclFile object

        This gives access to data vectors defined on the grid."""
        if not self._egridfile:
            egridfilename = self._eclbase + ".EGRID"
            if not Path(egridfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
            logger.info("Opening data vectors from EGRID file: %s", egridfilename)
            self._egridfile = EclFile(egridfilename)
        return self._egridfile

    def get_eclsum(self, include_restart=True):
        """Find and return the summary file and
        return as EclSum object

        Args:
            include_restart: boolean sent to libecl for whether restart files
                should be traversed.
        Returns:
            ecl.summary.EclSum
        """
        if not self._eclsum:
            smryfilename = self._eclbase + ".UNSMRY"
            if not Path(smryfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), smryfilename
                )
            logger.info("Opening UNSMRY file: %s", smryfilename)
            self._eclsum = EclSum(smryfilename, include_restart=include_restart)
        return self._eclsum

    def get_initfile(self):
        """Find and return the INIT file as an EclFile object"""
        if not self._initfile:
            initfilename = self._eclbase + ".INIT"
            if not Path(initfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), initfilename
                )
            logger.info("Opening INIT file: %s", initfilename)
            self._initfile = EclFile(initfilename)
        return self._initfile

    def get_rftfile(self):
        """Find and return the RFT file as an EclFile object"""
        if not self._rftfile:
            rftfilename = self._eclbase + ".RFT"
            if not Path(rftfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rftfilename
                )
            logger.info("Opening RFT file: %s", rftfilename)
            self._rftfile = EclFile(rftfilename)
        return self._rftfile

    def get_rstfile(self):
        """Find and return the UNRST file as an EclFile object"""
        if not self._rstfile:
            rstfilename = self._eclbase + ".UNRST"
            if not Path(rstfilename).is_file():
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rstfilename
                )
            logger.info("Opening RST file: %s", rstfilename)
            self._rstfile = EclFile(rstfilename)
        return self._rstfile

    def get_rstfilename(self):
        """Return the inferred name of the UNRST file"""
        return self._eclbase + ".UNRST"

    def get_prtfilename(self):
        """Return the inferred name of the PRT file"""
        return self._eclbase + ".PRT"

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

        zonelines = open(fullpath).readlines()
        zonelines = [line.strip() for line in zonelines]
        zonelines = [line.split("--")[0] for line in zonelines]
        zonelines = [line for line in zonelines if not line.startswith("#")]
        zonelines = filter(len, zonelines)

        zonemap = {}
        for line in zonelines:
            try:
                linesplit = shlex.split(line)
                map(str.strip, linesplit)
                filter(len, linesplit)
                (k_0, k_1) = "".join(linesplit[1:]).split("-")
                for k_idx in range(int(k_0), int(k_1) + 1):
                    zonemap[k_idx] = linesplit[0]
            except ValueError:
                logger.error("Could not parse zonemapfile %s", filename)
                logger.error("Failed on content: %s", line)
                return
        return zonemap


def rreplace(pat, sub, string):
    """Variant of str.replace() that only replaces at the end of the string"""
    return string[0 : -len(pat)] + sub if string.endswith(pat) else string  # noqa
