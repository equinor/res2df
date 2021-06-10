grid
----

The grid module will extract static and dynamic cell properties from
an Eclipse grid (from the binary output files from Eclipse). Each row
in a returned dataframe represents one cell.

Typical usage

.. code-block:: python

   from ecl2df import grid, EclFiles

   eclfiles = EclFiles('MYDATADECK.DATA')
   dframe = grid.df(eclfiles, rstdates='last')

where the API is documented at :func:`ecl2df.grid.df`.

..
   eclfiles = EclFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')
   grid.df(eclfiles).sample(10).to_csv('docs/usage/grid.csv', float_format="%.2f", index=False)

.. csv-table:: Example grid table
   :file: grid.csv
   :header-rows: 1


Alternatively, the same data can be produced as a CSV file using the command line

.. code-block:: console

  ecl2csv grid --help  # Will display some help text
  ecl2csv grid MYDATADECK.DATA --rstdates last --verbose --output grid.csv


Select which vectors to include (INIT and/or restart vectors) with the
``vectors`` argument, as in the example:

.. code-block:: console

  ecl2csv grid --verbose MYDATADECK.DATA --vectors PRESSURE PERMX

Example computations on a grid dataframe
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some grid statistic operations are very neatly expressed using Python and
Pandas. Some examples (provided that the ``dframe`` object is initialized as in
the topmost example):

Summation of floating point numbers is difficult for computers, as summing each
number in a sequence can lead to accumulation of roundoff errors. This is
proven to have an impact on volumetrics computations on a grid. For this, the
Python function ``math.fsum()`` should always be used.

.. code-block:: python

   # Average non-weighted porosity:
   dframe["PORO"].mean()

   # Bulk volume in Gm3:
   math.fsum(dframe["VOLUME"]) / 1e9

   # Total pore volume:
   math.fsum(dframe["PORV"])

   # Average (weighted) porosity:
   math.fsum(dframe["PORV"]) / math.fsum(dframe["VOLUME"])

   # Apex reservoir (cell centre):
   dframe["Z"].min()

   # Apex reservoir (topmost cell corner):
   dframe["Z_MIN"].min()


Pandas has powerful aggregation operators, and any thinkable statistical measure
can be applied to the data. The Pandas `groupby()` operation can be used to get
statistical measures pr. regions. All of the above examples can be rephrased to
compute values for every SATNUM, EQLNUM or similar. Example:

.. code-block:: ipython

   # Apex reservoir pr equilibriation zone
   In [3]: dframe.groupby(["EQLNUM"])["Z"].min()
   Out[3]:
   EQLNUM
   1.0    1568.876251
   2.0    1619.720749
   Name: Z, dtype: float64

Zone information
^^^^^^^^^^^^^^^^

As mentioned in :ref:`zone-names`, if the text file called `zones.lyr` is found
alongside, zone information will automatically be merged into each row based on the `K`
column. This can be used for statistics pr. zone,

.. code-block:: ipython

   # Permeability (arithmetic average) pr. zone
   In [4]: dframe.groupby("ZONE")["PERMX"].mean()
   Out[4]:
   ZONE
   LowerReek    979.605462
   MidReek      833.304757
   UpperReek    545.180473

If you have the layer information in a different file, you need to tell the code
the whereabouts of the file:

.. code-block:: python

   from ecl2df import grid, EclFiles, common

   eclfiles = EclFiles("'MYDATADECK.DATA")
   dframe = grid.df(eclfiles)
   # The filename with layers is relative to DATA-file location
   # or an absolute path.
   subzonemap = ecl2df.common.parse_zonemapfile("subzones.lyr")
   dframe_with_subzones = common.merge_zones(
       dframe, subzonemap, zoneheader="SUBZONE", kname="K"
   )

For more control over merging of zones, check the documentation for
the function :func:`ecl2df.common.merge_zones` and
:meth:`ecl2df.common.parse_zonemapfile`

Dynamic data
^^^^^^^^^^^^

By adding a restart date, dynamic data for one particular restart date can be
added, through the API option ``rstdates`` or the command line option
``--rstdates``.

You can write dates in ISO-8601 format, or you can specify *first*, *last* or
*all*.  If you select all dates, you can choose to have a set of columns for
every date, or have the date encoded in a column called ``DATE``, this is
controlled via the ``--stackdates`` option.

See also the :ref:`usage-pillars` module for an application of the grid data.
Calculating volumes of dynamic data (pr. some region parameter) can be obtained
from that module as a by-product of the pillar computations.


Generating Eclipse include files from grid data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have loaded grid data into a Pandas frame, some operations are easily performed,
scaling porosity, permeability etc. Or remapping some region parameters. Using the
:func:`ecl2df.grid.df2ecl()` function these manipulated vectors can be written back as
include files to Eclipse.

Say you want to change the FIPNUM, and that FIPNUM 6 should be removed, and set
it to FIPNUM 5. This can be accomplished using

.. code-block:: python

   from ecl2df import grid, EclFiles, common

   eclfiles = EclFiles("'MYDATADECK.DATA")
   dframe = grid.df(eclfiles)

   # Change FIPNUM 6 to FIPNUM 5:
   rows_to_touch = dframe["FIPNUM"] == 6
   dframe.loc[rows_to_touch, "FIPNUM"] = 5

   # Write back to new include file, ensure datatype is integer.
   grid.df2ecl(dframe, "FIPNUM", dtype=int, filename="fipnum.inc", eclfiles=eclfiles)

This will produce the file `fipnum.inc` with the contents:

.. literalinclude:: fipnum.inc

It is recommended to supply the ``eclfiles`` object to ``df2ecl``, if not, correct grid
size can not be ensured.
