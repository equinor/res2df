grid
----

The grid module will extract static and dynamic cell properties from
an Eclipse grid (from the binary output files from Eclipse). Each row
in a returned dataframe represents one cell.

Typical usage

.. code-block:: python

   from ecl2df import grid, EclFiles

   eclfiles = EclFiles('MYDATADECK.DATA')
   dframe = grid.df(eclfiles)

..
   eclfiles = EclFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')
   grid.df(eclfiles).sample(10).to_csv('docs/usage/grid.csv', float_format="%.2f", index=False)

.. csv-table:: Example grid table
   :file: grid.csv
   :header-rows: 1


Alternatively, the same data can be produced as a CSV file using the command line

.. code-block:: console

  ecl2csv grid MYDATADECK.DATA --verbose --output grid.csv


