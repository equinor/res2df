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
``vectors`` argument.

Example computations on a grid dataframe
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some grid statistic operations are very neatly expressed using Python and
Pandas. Some examples (provided that the ``drame`` object is initialized as in
the topmost example):

.. code-block:: python

   # Average non-weighted porosity:
   dframe["PORO"].mean()

   # Bulk volume in Gm3:
   dframe["VOUME"].sum() / 1e9

   # Total pore volume:
   dframe["PORV"].sum()

   # Average (weighted) porosity:
   dframe["PORV"].sum() / dframe["VOLUME"].sum()

   # Apex reservoir (cell centre):
   dframe["Z"].min()


Pandas has powerful aggregation operators, and any thinkable statistical measure
can be applied to the data. The Pandas `groupby()` operation can be used to get
statistical measures pr. regions. All of the above examples can be rephrased to
compute values for every SATNUM, EQLNUM or similar. Example:

.. code-block:: python

   # Apex reservoir pr equilibriation zone
   In[3]: dframe.groupby(["EQLNUM"])["Z"].min()
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

.. code-block:: python

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
   zonemap = eclfiles.get_zonemap("subzones.lyr")
   dframe_with_subzones = common.merge_zones(dframe, zonemap,
                                             zoneheader="SUBZONE")
                                             kname="K")

For more control over merging of zones, check the documentation for
the function :func:`ecl2df.common.merge_zones` and
:meth:`ecl2df.EclFiles.get_zonemap`

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

