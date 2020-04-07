pillars
-------

pillars is a module to compute data on "pillars" in the grid from an
Eclipse simulation, including both static and dynamic data from the grid.

Static data
^^^^^^^^^^^

Typical usage is to obtain property statistics, and compute contacts pr.
pillar (and optionally pr some region parameter).

..
  from ecl2df import pillars, EclFiles
  pillars.df(ecl2df.EclFiles('../tests/data/reek/eclipse/model/2_R001_REEK-0.DATA'))
  pillars.df(ecl2df.EclFiles('../tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).head().to_csv("pillars-example1.csv"float_format="%.1f", index=False))

.. csv-table:: Example pillar table
   :file: pillars-example1.csv
   :header-rows: 1

where the first ``PILLAR`` column is the ``I`` and ``J`` identification of the pillar.
and the other values are arithmetic averages of the values in the cells belonging
to a particular pillar. If you provide a region parameter (like ``EQLNUM``), the
value for the region will be added in an extra column called ``EQLNUM``.

Dynamic data
^^^^^^^^^^^^

The API :func:`ecl2df.pillars.df` and command line client allows specifying
dates if dynamic data should
be included through the ``rstdates`` option to the API or the ``--rstdates`` option
on the command line. Providing dates as an option will trigger computation of
phase volumes ``WATVOL``, ``OILVOL``, and ``GASVOL`` for each date.

If, in addition to dates, the parameters ``soilcutoff`` etc. are provided, these
are used to determine oil-water and/or gas-oil contacts pr pillar (and pr. region)


Stacked version
^^^^^^^^^^^^^^^

By default, dynamic data are added as a set of columns for every date, like in
this example:

..
  pillars.df(ecl2df.EclFiles('../tests/data/reek/eclipse/model/2_R001_REEK-0.DATA'), rstdates='all').dropna().head().to_csv('pillars-dyn1-unstacked.csv', float_format="%.1f", index=False)

.. csv-table:: Example pillar table with dynamical data, unstacked
   :file: pillars-dyn1-unstacked.csv
   :header-rows: 1

This may be what you want, however it is also possible to have ``DATE`` as a column,
obtained by triggering the stacking option in :func:`ecl2df.pillars.df` or
``--stackdates`` on the command line and get data like this:


.. csv-table:: Example pillar table with dynamical data, stacked
   :file: pillars-dyn1-stacked.csv
   :header-rows: 1
