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

from ecl.eclfile import EclFile
from ecl.grid import EclGrid


class EclFiles(object):
    def __init__(self, eclbase):
        # Strip .DATA or . at end of eclbase:
        eclbase = rreplace(".DATA", "", eclbase)
        eclbase = rreplace(".", "", eclbase)
        self._eclbase = eclbase

        # Set class variables to None
        self._egridfile = None  # Should be EclFile
        self._initfile = None  # Should be EclFile

        self._egrid = None  # Should be EclGrid

        self._rstfile = None  # EclFile

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

    def get_initfile(self):
        if not self._initfile:
            initfilename = self._eclbase + ".INIT"
            if not os.path.exists(initfilename):
                # Log warning
                return None
            self._initfile = EclFile(initfilename)
        return self._initfile

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
