.. _usage-pillars:

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

where the first ``PILLAR`` column is the ``I`` and ``J`` identification of the
pillar.  and the other values are arithmetic averages of the values in the cells
belonging to a particular pillar.

If you provide a region parameter (like ``EQLNUM``), the value for the region
will be added in an extra column called ``EQLNUM``. Each pillar will then be
repeated for each region value where it exists.


Dynamic data, volumes and fluid contacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The API :func:`ecl2df.pillars.df` and command line client allows specifying
dates if dynamic data should be included through the ``rstdates`` option to the
API or the ``--rstdates`` option on the command line. Providing dates as an
option will trigger computation of phase volumes ``WATVOL``, ``OILVOL``, and
``GASVOL`` for each date.

If, in addition to dates, the parameters ``soilcutoff`` etc. are provided, these
are used to determine oil-water and/or gas-oil contacts pr pillar (and pr.
region).

An oil-water contact pr. pillar is determined as the deepest cell
centre with SOIL above the given contact, among those pillars with at least one
cell above ``swatcutoff``.

A gas-oil contact is the deepest cell
centre with SGAS above the cutoff ``sgascutoff``, among those pillars with at
least one cell with non-zero oil saturation.

Gas-water contact is only computed when ``SOIL`` is not present in the
simulation (two-phase runs), it will be the deepest cell centre with gas
saturation above sgascutoff, among those pillars with at least one cell above
``swatcutoff``. See the API documentation,
:func:`ecl2df.pillars.compute_pillar_contacts`.

The functionality is also available through the command line tool ``ecl2csv pillars``
as in the example:

.. code-block:: console

   ecl2csv pillars --help  # This will display some help text
   ecl2csv pillars MYDATAFILE.DATA --rstdates all --stackdates

It is *strongly* recommended to play with the cutoffs to get the desired result.
Also calibrate the computed contacts with the initial contacts, you may see that
you should add a constance distance to all computed contacts. Beware that shale
cells with little oil, but in the oil zone necessarily will affect the
computation (sometimes that explains the need for calibration to initial
contacts).

Grouping data
^^^^^^^^^^^^^

It is possible to aggregate data over all pillars after computation. Activate
using ``--group`` to the command line client, and add optionally a ``--region``
parameter to group over a particular region, typically ``EQLNUM``.

The Python API will group over any data that is supplied via the ``region``
option, check :func:`ecl2df.pillars.df`


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
