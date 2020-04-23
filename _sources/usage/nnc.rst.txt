nnc
---

nnc will extract Non-Neighbour-Connections from your Eclipse grid as pairs
of *ijk* indices together with their associated transmissibilities.

See also the :doc:`trans` module, which can extract all transmissibilities, not only
non-neigbour connections.

..
  nnc.df(EclFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).head(15).to_csv('docs/usage/nnc.csv', index=False)

.. code-block:: python

   from ecl2df import nnc, EclFiles

   eclfiles = EclFiles('MYDATADECK.DATA')
   dframe = nnc.df(eclfiles)

.. csv-table:: Example nnc table
   :file: nnc.csv
   :header-rows: 1


Alternatively, the same data can be produced as a CSV file using the command line

.. code-block:: console

  ecl2csv nnc MYDATADECK.DATA --verbose --output nnc.csv

It is possible to add *xyz* coordinates for each connection (as the
average of the xyz for each of the cells involved in a connection pair) as
extra columns.

If you only want vertical connections, add the option ``--pillars`` or ``-vertical``,
or set ``pillars=True`` if using the Python API (:func:`ecl2df.nnc.df`)


