equil
-----

This is the ecl2df module for processing the ``SOLUTION`` section of
the Eclipse input deck.

Supported keywords are ``EQUIL``, ``RSVD``, ``RVVD``, ``PBVD`` and
``PDVD``. Typical usage is

.. code-block:: python

    from ecl2df import equil, EclFiles

    dframe = equil.df(EclFiles('MYECLDECK.DATA'))

Which will provide a dataframe similar to the example below. Note that the column
`Z` is used both for datum depth and the depth values in ``RSVD`` tables. The
amount of columns obtained depends on the input dataset, and should be possible
to link up with the Eclipse documentation. API doc: :func:`ecl2df.equil.df`

..
  dframe = equil.df(EclFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA'))
  dframe[['EQLNUM', 'KEYWORD', 'Z', 'PRESSURE', 'OWC', 'GOC', 'RS']]\
  .to_csv(index=False))

.. csv-table:: Equil dataframe example
   :file: equil-example.csv
   :header-rows: 1

The dataframe obtained can be exported to CSV using ``.to_csv()`` for further
processing or visualization, or it can be transformed using Python (Pandas)
operations.

Transforming data
^^^^^^^^^^^^^^^^^

Shifting all oil-water contacts down by one meter could for example
be accomplished by the operation

.. code-block:: python

   dframe["OWC"] = dframe["OWC"] + 1

This statement will not interfere with the ``RSVD`` lines, as they are NaN for
this column. But still, you might want to push your `Rs` initialization down
one meter for compatibility, which you could do by the statements:

.. code-block:: python

   rsvd_rows = dframe["KEYWORD"] == "RSVD"
   dframe.loc[rsvd_rows, "Z"] = dframe.loc[rsvd_rows, "Z"] + 1


Re-exporting tables to Eclipse include files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you are done with the table, you can generate new include files for
Eclipse from your modified data by issuing

.. code-block:: python

   equil.df2ecl(dframe, filename="solution.inc")

The last step can also be done using the ``csv2ecl`` command line utility
if you dump to CSV from your Python code instead.
