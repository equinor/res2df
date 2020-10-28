wcon
^^^^

This module extracts information from WCONHIST, WCONINJE, WCONINJH and
WCONPROD from an Eclipse deck.

..
  wcon.df(EclFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).head(15).to_csv('docs/usage/wcon.csv', index=False)
.. code-block:: python

   from ecl2df import wcon, EclFiles

   eclfiles = EclFiles("MYDATADECK.DATA")
   dframe = wcon.df(eclfiles)

.. csv-table:: Example WCON table
   :file: wcon.csv
   :header-rows: 1
