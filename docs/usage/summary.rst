summary
^^^^^^^

This module extracts summary information from :term:`UNSMRY-files <output file>` into
Pandas Dataframes.

..
  summary.df(ResdataFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA'), column_keys="F*PT", time_index='yearly').to_csv("summary.csv")

.. code-block:: python

   from res2df import summary, ResdataFiles

   resdatafiles = ResdataFiles("MYDATADECK.DATA")
   dframe = summary.df(resdatafiles, column_keys="F*PT", time_index="yearly")

If you don't specify ``column_keys``, all included summary vectors will be
retrieved. Default for ``time_index`` is the report datetimes written by
Eclipse equivalent to ``time_index="raw"``, other options are *daily*, *weekly*,
*monthly* or *yearly*.  See below for how to interpred "interpolated" summary
data.

Additional arguments are available, see the
`API documentation <https://equinor.github.io/res2df/res2df/res2df.summary.html#res2df.summary.df>`_
for an extensive overview.

.. csv-table:: Example summary table
   :file: summary.csv
   :header-rows: 1

Rate handling in Eclipse summary vectors
========================================

Eclipse summary vectors with of rate type (oil rate, water rate etc.) are to be
interpreted carefully. A value of e.g. FOPR at a specific date means that the
value is valid *backwards* in time, until the prior point in time where data is
available. For correct rates, you must use the raw time index for get_smry(),
anything else will only give you an approximation. Also, you can not assume that
summing the rates at every point in time corresponds to the associated
cumulative summary vectors, e.g. FOPT, as there are multiple features into play
here with efficienty factors etc.
