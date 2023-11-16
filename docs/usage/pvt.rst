pvt
---

Extracts PVT related keyword data from the PROPS section in a :term:`.DATA file`,
typically the keywords ``PVTO``, ``PVDG``, ``DENSITY`` and ``ROCK``. Data from
all keywords will be merged into one common dataframe.

Example usage:

.. code-block:: python

   from res2df import pvt, ResdataFiles

   resdatafiles = ResdataFiles("MYDATADECK.DATA")
   dframe = pvt.df(resdatafiles)

Alternatively, we may also read directly from an :term:`include file`
if we read the contents of the file and supply it as a string:

.. code-block:: python

   dframe = pvt.df(open("pvt.inc").read())

..
  pvt.df(ResdataFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).tail(15).to_csv('docs/usage/pvt.csv', index=False)


.. csv-table:: Example PVT table (last 15 rows to show non-Nan data)
  :file: pvt.csv
  :header-rows: 1

If your PVT data resides in multiple include files, but you can't import
the entire :term:`deck`, you have to merge the dataframes in Python like this:

.. code-block:: python

   import pandas as pd

   pvto = pvt.df(open("pvto.inc").read())
   density = pvt.df(open("density.inc").read())
   pvt_df = pd.concat([pvto, density], ignore_index=True)

Transforming PVT data
^^^^^^^^^^^^^^^^^^^^^

Care should be taken when perturbing PVT data, as a lot
of the data values depend on each other for physical consistency.

A simple example could be to scale the viscosity values up or down with
some scalar amount:

.. code-block:: python

   # Scale up all viscosity values by 10%
   dframe["VISCOSITY"] = dframe["VISCOSITY"] * 1.1

Possibly, different viscosity scaling pr. PVTNUM is needed

.. code-block:: python

   # Scale up all viscosity values by 10% in PVTNUM 1 and by 5% in 2
   pvtnum1_rows = dframe["PVTNUM"] == 1
   pvtnum2_rows = dframe["PVTNUM"] == 2
   dframe.loc[pvtnum1_rows, "VISCOSITY"] = dframe.loc[pvtnum1_rows, "VISCOSITY"] * 1.05

(there are many ways of doing operation on specific PVTNUMs in Pandas, pick your favourite).

Density values are easier to scale up or down to whatever is needed.

Re-exporting tables to include files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you are done with the table, you can generate new 
:term:`include files <include file>` from your modified data by issuing

.. code-block:: python

   pvt.df2res(dframe, filename="pvt.inc")

When injecting this produced ``pvt.inc`` into any new :term:`.DATA file`, ensure you
check which keywords have been written out, compared to what you gave in to
`res2df.pvt` above. Any non-supported keywords will get lost in the import phase
and need to be catered for outside res2df.

The last step can also be done using the ``csv2res`` command line utility
if you dump to CSV from your Python code instead.

