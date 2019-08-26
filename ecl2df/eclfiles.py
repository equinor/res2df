# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import errno

import sunbeam.deck

from ecl.eclfile import EclFile
from ecl.grid import EclGrid
from ecl.summary import EclSum

# Default parse option to Sunbeam for a very permissive parsing
SUNBEAM_RECOVERY = [
    ("PARSE_UNKNOWN_KEYWORD", sunbeam.action.ignore),
    ("SUMMARY_UNKNOWN_GROUP", sunbeam.action.ignore),
    ("PARSE_RANDOM_SLASH", sunbeam.action.ignore),
    ("UNSUPPORTED_*", sunbeam.action.ignore),
    ("PARSE_MISSING_SECTIONS", sunbeam.action.ignore),
    ("PARSE_MISSING_DIMS_KEYWORD", sunbeam.action.ignore),
    ("PARSE_RANDOM_TEXT", sunbeam.action.ignore),
    ("PARSE_MISSING_INCLUDE", sunbeam.action.ignore),
    ("PARSE_EXTRA_RECORDS", sunbeam.action.ignore),
]

# For Python2 compatibility:
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


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

    def get_ecldeck(self):
        """Return a sunbeam deck of the DATA file"""
        if not self._deck:
            if os.path.exists(self._eclbase + ".DATA"):
                deckfile = self._eclbase + ".DATA"
            else:
                deckfile = self._eclbase  # Will be any filename
            deck = sunbeam.deck.parse(deckfile, recovery=SUNBEAM_RECOVERY)
            self._deck = deck
        return self._deck

    @staticmethod
    def str2deck(string, recovery=None):
        """Produce a sunbeam deck from a string, using permissive
        parsing by default"""
        if not recovery:
            recovery = SUNBEAM_RECOVERY
        return sunbeam.deck.parse_string(string, recovery=recovery)

    @staticmethod
    def file2deck(filename):
        """Try to convert standalone files into Sunbeam Deck objects"""
        with open(filename) as fhandle:
            filestring = "".join(fhandle.readlines())
            return EclFiles.str2deck(filestring)

    def get_egrid(self):
        """Find and return EGRID file as an EclGrid object"""
        if not self._egrid:
            egridfilename = self._eclbase + ".EGRID"
            if not os.path.exists(egridfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
            self._egrid = EclGrid(egridfilename)
        return self._egrid

    def get_egridfile(self):
        """Find and return the EGRID file as a EclFile object"""
        if not self._egridfile:
            egridfilename = self._eclbase + ".EGRID"
            if not os.path.exists(egridfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), egridfilename
                )
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
            if not os.path.exists(smryfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), smryfilename
                )
            self._eclsum = EclSum(smryfilename, include_restart=include_restart)
        return self._eclsum

    def get_initfile(self):
        """Find and return the INIT file as an EclFile object"""
        if not self._initfile:
            initfilename = self._eclbase + ".INIT"
            if not os.path.exists(initfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), initfilename
                )
            self._initfile = EclFile(initfilename)
        return self._initfile

    def get_rftfile(self):
        """Find and return the RFT file as an EclFile object"""
        if not self._rftfile:
            rftfilename = self._eclbase + ".RFT"
            if not os.path.exists(rftfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rftfilename
                )
            self._rftfile = EclFile(rftfilename)
        return self._rftfile

    def get_rstfile(self):
        """Find and return the UNRST file as an EclFile object"""
        if not self._rstfile:
            rstfilename = self._eclbase + ".UNRST"
            if not os.path.exists(rstfilename):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), rstfilename
                )
            self._rstfile = EclFile(rstfilename)
        return self._rstfile

    def get_rstfilename(self):
        """Return the inferred name of the UNRST file"""
        return self._eclbase + ".UNRST"


def rreplace(pat, sub, string):
    """Variant of str.replace() that only replaces at the end of the string"""
    return string[0 : -len(pat)] + sub if string.endswith(pat) else string
