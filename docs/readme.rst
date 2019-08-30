Introduction
============

*ecl2df* is a `Pandas DataFrame <https://pandas.pydata.org/>`_ wrapper
around `libecl <https://github.com/equinor/libecl/>`_ and `sunbeam
<https://github.com/equinor/sunbeam/>`_, which are used to access
binary files outputted by the reservoir simulator Eclipse, or its
input files --- or any other tool outputting to the same data format,
f.ex. `flow <https://opm-project.org/?page_id=19>`_.

Most of the features can be reached from the command line, through the
command line program ecl2csv.

Module overview
---------------

``summary2df``
^^^^^^^^^^^^^^

Extracts summary data from `.UNSMRY` files, at requested time sampling and
for requested vectors.

``grid2df``
^^^^^^^^^^^

Extracts grid data from `.INIT` and `.EGRID` and `.UNRST` files. Restart files are optional to extract, and dates must be picked (or all). Data is
merged into one DataFrame by the `i`, `j` and `k` indices. Bulk cell
volume is included.

``nnc2df``
^^^^^^^^^^

Extracts the non-neighbour connections in the grid, as pairs of
`ijk`-indices and the associated transmissiblity.

``rft2df``
^^^^^^^^^^

Reads the `.RFT` files which are outputted by the simulator when
the `WRFTPLT` keyword is used, with details along wellbores.

For multisegment wells, the well topology is calculated and data
is merged accordingly, for example when ICD segments are used, enabling
easy calculations of the pressure drop over an ICD valve.

``satfunc2df``
^^^^^^^^^^^^^^

Extracts saturation functions (SWOF, SGOF, etc) from the deck and merges
into one DataFrame.

``equil2df``
^^^^^^^^^^^^

Extracts the information in the `EQUIL` table in the input deck.

``compdat2df``
^^^^^^^^^^^^^^

Extracts well connection data from the `COMPDAT` keyword in the input deck.
For multi-segment wells, `WELSEGS` and `COMPSEGS` is also parsed. The
data is available as three different dataframes, which can be merged.

It is also possible to parse individual "include" files, not only a
finished working deck.

``gruptree2df``
^^^^^^^^^^^^^^^

Extracts the information from the `GRUPTREE` and `WELSPECS` keyword, at
all timesteps, from the input deck. The tree structure at each relevant
date can be returned as a dataframe of the edges, as a nested dictionary
or as a `treelib` tree.

``eclfiles``
^^^^^^^^^^^^

This is an internal helper module in order to represent finished or
unfinished Eclipse decks and runs. The class EclFiles can cache binary
files that are recently read, and is able to locate the various output
files based on the basename or the `.DATA` filename.

License
-------

This library is released under GPLv3.

Copyright
---------

The code is Copyright Equinor ASA 2019.

Contributions without copyright transfer are welcome.
