compdat
^^^^^^^

This module extracts COMPDAT, WELSEGS and COMPSEGS from an Eclipse deck.

Additionally, it will parse WELOPEN statements and emit new COMPDAT
statements from the actions in WELOPEN.

..
  compdat.df(EclFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).head(15).to_csv('docs/usage/compdat.csv', index=False)
.. code-block:: python

   from ecl2df import compdat, EclFiles

   eclfiles = EclFiles("MYDATADECK.DATA")
   dframe = compdat.df(eclfiles)

.. csv-table:: Example COMPDAT table
   :file: compdat.csv
   :header-rows: 1

If you need access to WELSEGS, COMPSEGS, WSEGSICD, WSEGAICD or WSEGVALV, you
must use the ``deck2dfs()`` function which will return a dict with dataframes
for each of COMPDAT, and the segmentation keywords.

.. warning:: When WELOPEN is in use, the dataframe can differ from Eclipse
  behaviour in certain circumstances. The dataframe representation from
  ``compdat`` does not separate from a "shut" well and the open-ness of its
  connections. So in an Eclipse deck it is possible to shut a well, and then
  reopen it, and get back the original open/shut state of individual
  connections prior to well shut.  The dataframe format will display `all`
  connections as open if a well is opened with defaulted indices.

Adding INIT data
----------------

Additional information from the grid for each connection (based on i, j, k) can
be added to the returned data through the option ``--initvectors``:

.. code-block:: console

   ecl2csv compdat --verbose MYDATADECK.DATA --initvectors FIPNUM PERMX
   # (put the DATA file first, if not it will be interpreted as a vector)
