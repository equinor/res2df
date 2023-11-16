wcon
^^^^

This module extracts information from WCONHIST, WCONINJE, WCONINJH and
WCONPROD from a :term:`.DATA file`.

..
  wcon.df(ResdataFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).head(15).to_csv('docs/usage/wcon.csv', index=False)
.. code-block:: python

   from res2df import wcon, ResdataFiles

   resdatafiles = ResdataFiles("MYDATADECK.DATA")
   dframe = wcon.df(resdatafiles)

.. csv-table:: Example WCON table
   :file: wcon.csv
   :header-rows: 1
