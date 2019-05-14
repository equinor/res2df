# -*- coding: utf-8 -*-
"""
Class for holding an Eclipse deck with result files

Exists only for convenience, so that loading of
EclFile/EclSum objects is easy for users, and with
caching if wanted.

Various functions that needs some of the Eclipse output
(or input file) should be able to ask this class, and
it should be loaded or served from cache.
"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os

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
]


class EclFiles(object):
    def __init__(self, eclbase):
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
        if not self._deck:
            if os.path.exists(self._eclbase + ".DATA"):
                deckfile = self._eclbase + ".DATA"
            else:
                deckfile = self._eclbase  # Will be any filename
            deck = sunbeam.deck.parse(deckfile, recovery=SUNBEAM_RECOVERY)
            self._deck = deck
        return self._deck

    @staticmethod
    def str2deck(string):
        return sunbeam.deck.parse_string(string, recovery=SUNBEAM_RECOVERY)

    @staticmethod
    def file2deck(file):
        """Try to convert standalone files into Sunbeam Deck objects"""
        with open(file) as f:
            filestring = "".join(f.readlines())
            return EclFiles.str2deck(filestring)

    def get_egrid(self):
        """Return EGRID file as EclGrid"""
        if not self._egrid:
            egridfilename = self._eclbase + ".EGRID"
            if not os.path.exists(egridfilename):
                # Log warning to user
                return None
            self._egrid = EclGrid(egridfilename)
        return self._egrid

    def get_egridfile(self):
        if not self._egridfile:
            egridfilename = self._eclbase + ".EGRID"
            if not os.path.exists(egridfilename):
                # Log warning to user
                return None
            self._egridfile = EclFile(egridfilename)
        return self._egridfile

    def get_eclsum(self):
        print(self._eclsum)
        if not self._eclsum:
            smryfilename = self._eclbase + ".UNSMRY"
            print(smryfilename)
            if not os.path.exists(smryfilename):
                # Log warning
                return None
            print("Loading eclsum from " + smryfilename)
            self._eclsum = EclSum(smryfilename)
        return self._eclsum

    def get_initfile(self):
        if not self._initfile:
            initfilename = self._eclbase + ".INIT"
            if not os.path.exists(initfilename):
                # Log warning
                return None
            self._initfile = EclFile(initfilename)
        return self._initfile

    def get_rftfile(self):
        if not self._rftfile:
            rftfilename = self._eclbase + ".RFT"
            if not os.path.exists(rftfilename):
                print("File " + rftfilename + " not found")
                return None
            self._rftfile = EclFile(rftfilename)
        return self._rftfile

    def get_rstfile(self):
        if not self._rstfile:
            rstfilename = self._eclbase + ".UNRST"
            if not os.path.exists(rstfilename):
                # Log warning
                return None
            self._rstfile = EclFile(rstfilename)
        return self._rstfile

    def get_rstfilename(self):
        return self._eclbase + ".UNRST"


# Static method
def rreplace(pat, sub, string):
    """Variant of str.replace() that only replaces at the end of the string"""
    return string[0 : -len(pat)] + sub if string.endswith(pat) else string
