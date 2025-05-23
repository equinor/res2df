Introduction
============

*res2df* is a `Pandas DataFrame <https://pandas.pydata.org/>`_ wrapper
around `resdata <https://github.com/equinor/resdata/>`_ and `opm.io
<https://github.com/OPM/opm-common/>`_, which are used to access
:term:`binary files outputted by reservoir simulators <output file>` such as Eclipse, or its
:term:`input files <deck>` --- or any other tool outputting to the same data format,
f.ex. `flow <https://opm-project.org/?page_id=19>`_.

Most of the features can be reached from the command line, through the
command line program ``res2csv``. Use the command line tool to dump the
extracted or computed data to a CSV file, and use any other tool to
view the CSV data.

Examples
--------

.. code-block:: console

    > res2csv --help
    > res2csv summary --help
    > res2csv summary --column_keys "F*" --time_index monthly --output output.csv MYDECK.DATA
    > res2csv pillars --help
    > res2csv pillars --rstdates all MYDECK.DATA

If you access the module from within a Python script, for each submodule
there is a function called ``df()`` which provides more or less the same
functionality as through ``res2csv`` from the command line, but which returns
a Pandas Dataframe.

.. code-block:: python

    import res2df

    resdatafiles = res2df.ResdataFiles("MYDECK.DATA")
    smry = res2df.summary.df(resdatafiles, column_keys="F*", time_index="monthly")
    hc_contacts = res2df.pillars.df(resdatafiles, rstdates="all")

See the API for more documentation and possibilities for each module.

Short description of each submodule
-----------------------------------

``summary``
^^^^^^^^^^^^^^

Extracts summary data from :term:`.UNSMRY <output file>` files, at requested time sampling and
for requested vectors.

More documentation on :doc:`usage/summary`.

``grid``
^^^^^^^^

Extracts grid data from :term:`.INIT <output file>`, :term:`.EGRID <output file>`,
and :term:`.UNRST <output file>` files. Restart file
are optional to extract, and dates must be picked (or all). Data is
merged into one DataFrame by the `i`, `j` and `k` indices. Bulk cell
volume is included. Cells are indexed starting with 1.

More documentation on :doc:`usage/grid`.

``nnc``
^^^^^^^

Extracts the non-neighbour connections in the grid (from the binary
output data in EGRID, not the NNC input keyword), as pairs of
`ijk`-indices and the associated transmissiblity. Optional filtering
to vertical connections (along pillars).

More documentation on :doc:`usage/nnc`.

``pillars``
^^^^^^^^^^^

Compute statistics pr cornerpoint pillar, and optionally compute hydrocarbon
fluid contacts pr. pillar and pr. date based on saturation cutoffs. Data
can be grouped and aggregated over a region parameter.

More documentation on :doc:`usage/pillars`.

``trans``
^^^^^^^^^

Extract transmissibilities for all cells. Can filter by directions, add
transmissibilities from NNC-data. If a region vector is supplied, it is
possible to filter on transmissibilities where the region changes, picking
out transmissibilities over f.ex. a FIPNUM interface. Data can also be aggregated
over the region interface to give a grid-independent quantification of region
communication.

More documentation on :doc:`usage/trans`.

``rft``
^^^^^^^

Reads the `.RFT` files which are outputted by the
:term:`simulator <reservoir simulator>` when
the `WRFTPLT` keyword is used, with details along wellbores.

For multisegment wells, the well topology is calculated and data
is merged accordingly, for example when ICD segments are used, enabling
easy calculations of the pressure drop over an ICD valve.

More documentation on :doc:`usage/rft`.

``fipreports``
^^^^^^^^^^^^^^

Parses the PRT file looking for region reports (starting
with " ... FIPNUM REPORT REGION"). It will extract all the data
in the ASCII table in the PRT file and organize into a dataframe,
currently-in-place, outflow to wells, outflows to regions, etc. It also
supports custom FIPxxxxx names.

More documentation on :doc:`usage/fipreports`.


``satfunc``
^^^^^^^^^^^

Extracts saturation functions (SWOF, SGOF, etc) from the :term:`deck` and merges
into one DataFrame. Can write back to :term:`include files <include file>`.

More documentation on :doc:`usage/satfunc`.

``equil``
^^^^^^^^^

Extracts the information in the `EQUIL` table, `RSVD` and `RVVD` in the
:term:`.DATA file`. Can write back to :term:`include files <include file>`.

More documentation on :doc:`usage/equil`.

``compdat``
^^^^^^^^^^^

Extracts well connection data from the `COMPDAT` keyword in the :term:`deck`.
For multi-segment wells, `WELSEGS` and `COMPSEGS` is also parsed. The
data is available as three different dataframes, which can be merged.

It is also possible to parse individual :term:`"include files" <include file>`.
These files do not necessarily have to be part of a complete :term:`deck`

More documentation on :doc:`usage/compdat`.

``gruptree``
^^^^^^^^^^^^

Extracts the information from the `GRUPTREE` and `WELSPECS` keyword, at
all timesteps, from the :term:`.DATA file`. The tree structure at each relevant
date can be returned as a dataframe of the edges, as a nested dictionary
or as a `treelib` tree.

More documentation on :doc:`usage/gruptree`.

``pvt``
^^^^^^^

Extracts PVT data from a :term:`.DATA file`, from the keywords `PVTO`, `PVDG`,
`DENSITY`, `ROCK` etc. Can write data back to :term:`include files <include file>`.

More documentation on :doc:`usage/pvt`.

``wcon``
^^^^^^^^

Extracts `WCONxxxx` keywords from the Schedule section, and providing the
associated data in a dataframe format.

More documentation on :doc:`usage/wcon`.

``resdatafiles``
^^^^^^^^^^^^^^^^

This is an internal helper module in order to represent finished or
unfinished :term:`.DATA files <.DATA file>` and runs. The class ResdataFiles can cache binary
files that are recently read, and is able to locate the various
:term:`output files <output file>` based on the basename or the `.DATA` filename.

Metadata support
----------------

parameters.txt
^^^^^^^^^^^^^^

Metadata for each :term:`.DATA file` are sometimes added in a text file named
``parameters.txt``, alongside the Eclipse .DATA file or one or two directory levels
above it.

Each line in the text file should contain a string, interpreted as the key, and
a value for the key, which can be a string or number. Some modules can merge this
information onto each row, where the key in the parameters end up as column names.

The filenames ``parameters.json`` and ``parameters.yml`` are also supported, assumed
to be of JSON or YAML format respectively, but only one of them will be parsed.

Currently only supported by the summary module, for other modules, the data will
have to be merged with pandas.merge().

.. _zone-names:

Zone names
^^^^^^^^^^

If a text file with zone names are found alongside :term:`.DATA files <.DATA file>`,
some of the modules will add that information to rows where appropriate.
The zone or layer file should contains lines like::

  'ZoneA' 1-4
  'ZoneB' 5-10

The default filename looked for is ``zones.lyr``.

License
-------

This library is released under GPLv3.

Copyright
---------

The code is Copyright Equinor ASA 2019-2020.

Contributions without copyright transfer are welcome.
