nnc
---

nnc will extract Non-Neighbour-Connections from your grid as pairs
of *ijk* indices together with their associated transmissibilities.

See also the :doc:`trans` module, which can extract all transmissibilities, not only
non-neigbour connections.

Note: Eclipse300 will not export TRANNNC data in parallel mode.
Run in serial to get this output.

..
  nnc.df(ResdataFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).head(15).to_csv('docs/usage/nnc.csv', index=False)

.. code-block:: python

   from res2df import nnc, ResdataFiles

   resdatafiles = ResdataFiles('MYDATADECK.DATA')
   dframe = nnc.df(resdatafiles)

.. csv-table:: Example nnc table
   :file: nnc.csv
   :header-rows: 1


Alternatively, the same data can be produced as a CSV file using the command line

.. code-block:: console

  res2csv nnc MYDATADECK.DATA --verbose --output nnc.csv

It is possible to add *xyz* coordinates for each connection (as the
average of the xyz for each of the cells involved in a connection pair) as
extra columns.

If you only want vertical connections, add the option ``--pillars`` or ``-vertical``,
or set ``pillars=True`` if using the Python API (:func:`res2df.nnc.df`)

``EDITNNC`` export
^^^^^^^^^^^^^^^^^^

Data for the ``EDITNNC`` keyword can be dumped, in order to scale the NNC connections
using Pandas operations. Select the connections you want to scale by slicing
the nnc dataframe (either from the nnc module, or from the trans module), and fill
transmissibility multipliers in a new column ``TRANM``, then this can be exported
to an :term:`include file: <include file>`

.. code-block:: python

   from res2f import nnc, ResdataFiles

   resdatafiles = ResdataFiles("MYDATADECK.DATA")
   nnc_df = nnc.df(resdatafiles)
   nnc_df["TRANM"] = 0.1  # Reduce all NNC transmissibilities

   nnc.df2res_editnnc(nnc_df, filename="editnnc.inc")

and the contents of the exported file can be:

..
   print(nnc.df2res_editnnc(nnc.df(resdatafiles).head(4).assign(TRANM=0.1)))

.. code-block:: console

    EDITNNC
    --  I1  J1  K1  I2  J2  K2  TRANM
        30   4   2  31   4   1    0.1 /
        30   4   3  31   4   1    0.1 /
        30   4   3  31   4   2    0.1 /
        30   4   4  31   4   1    0.1 /
    / -- 4 nnc connections, avg multiplier 0.1

