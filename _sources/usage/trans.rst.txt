trans
-----

The trans module can extract transmissibilities (neighbour and non-neigbor-connections)
from a simulation grid.

Python API: :func:`ecl2df.trans.df`

Applied on an Eclipse deck, the *trans* module will give out a dataframe of neighbour
connections

.. code-block:: python

   from ecl2df import trans, EclFiles

   eclfiles = EclFiles("MYDATADECK.DATA")
   dframe = ecl2df.trans.df(eclfiles)

..
   ecl2df.trans.df(ecl2df.EclFiles("2_R001_REEK-0.DATA")).sample(7)\
   .to_csv("trans1.csv", float_format="%.2f", index=False)

.. csv-table:: Neighbour transmissibilities, sample rows from an example simulation.
   :file:  trans1.csv
   :header-rows: 1

The last column ``DIR`` is the direction of the connection in i-j-k, space, and can
take on the values ``I``, ``J``, and ``K``. The ``TRAN`` column has values from the
``TRANX``, ``TRANY`` or ``TRANZ`` in the Eclipse output files.

You can obtain this dataframe as a CSV file by writing this command on the
command line:

.. code-block:: console

   ecl2csv trans MYDATADECK.DATA --verbose --output trans.csv

Adding more data for each connection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can add ``coords=True`` to the ``df()`` call, which will add the columns ``X``,
``Y``, ``Z`` (which will be the average of the coordinates for the two cell
centerpoints) and also ``DX``, ``DY`` and ``DZ`` being the distance between the
two cells centerpoints. If using the command line client, the option is called
``--coords``.

Extra INIT (static data) vectors can be added, of particular interest is perhaps
some region parameter like ``FIPNUM`` or ``EQLNUM``, through the ``vectors`` argument.
For such vectors, there will be one column ``FIPNUM1`` and another column ``FIPNUM2``
for the other cell in the cell pair. This is often used together with filtering,
see below.

Non-neighbour connections can be added the dataframe by supplying the option
``addnnc=True``. These connections will have the string ``NNC`` in the ``DIR``
column.



Filtering connections
^^^^^^^^^^^^^^^^^^^^^

The API supports some filtering directly in the ``df()`` function call for
convenience.

Simple filtering based on vertical vs horizontal can be accomplished
by the options ``onlyijdir=True`` or  ``onlykdir=True``, or through the command line
options ``--onlyk`` or ``--onlyij``. Filtering is only a selection of which
the Eclipse vectors ``TRANX``, ``TRANY`` and ``TRANZ`` to include.

Note that the filtering only applies to neighbour connections. If you also choose
to add NNC-connections, these will still be added  to the dataframe with no filtering.

If you have added (only one) an INIT vector, typically a region parameter like
``FIPNUM`` or ``EQLNUM``, you have the option to filter to those connections
where this region parameter *changes*, which implies the connection is over
a region boundary. This is accomplished by providing a vector to include, and the
option ``boundaryfilter``. It is recommmended to include NNC in applications
like this. Example:

.. code-block:: python

   dframe = ecl2df.trans.df(eclfiles, vectors="FIPNUM", boundaryfilter=True, addnnc=True)

which gives the dataframe

..
   ecl2df.trans.df(ecl2df.EclFiles("2_R001_REEK-0.DATA"), addnnc=True, vectors="FIPNUM", boundaryfilter=True).sample(10).to_csv("trans-boundaries.csv", index=False, float_format="%.2f")

.. csv-table:: Sample rows from connections where FIPNUM is changing
   :file:  trans-boundaries.csv
   :header-rows: 1

If you also append coordinates to this dataframe, it would be possible to visualize
all your region connections in 3D, coloured by transmissibility.


Aggregating connection data over region interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The example above with filtering to wherever for example ``FIPNUM`` is changing,
naturally leads over to an application where transmissibility data is aggregated
over a region interface. This is accomplished by adding the ``group=True`` option.
(this requires one INIT vector to have been specified, and it implicitly implies
``boundaryfilter=True``). NNC is not required, but recommended.

.. code-block:: python

   from ecl2df import trans, EclFiles

   eclfiles = EclFiles("MYDATADECK.DATA")
   dframe = ecl2df.trans.df(eclfiles, vectors="FIPNUM", addnnc=True, group=True)

..
   ecl2df.trans.df(ecl2df.EclFiles("2_R001_REEK-0.DATA"), addnnc=True, vectors="FIPNUM", group=True).to_csv("trans-group.csv", index=False, float_format="%.2f")

.. csv-table:: Transmissibilities summed over each FIPNUM interface
   :file: trans-group.csv
   :header-rows: 1

where this last table can also be exported directly from the command line using

.. code-block:: console

   ecl2csv trans MYDATADECK.DATA --vectors FIPNUM --nnc --group --output fipnuminterfaces.csv

