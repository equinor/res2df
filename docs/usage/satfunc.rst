satfunc
-------

satfunc will extract saturation functions from :term:`.DATA files <.DATA file>` or from
:term:`include files <include file>`, these are the keywords ``SWOF``, ``SGOF``, 
``SGWFN``, ``SWFN``, ``SOF2``, ``SGFN``, ``SOF3`` and  ``SLGOF``.

The data obtained from one invocation of the satfunc module will be put in one
dataframe, where data from different keywords are separated by the ``KEYWORD``
column.

..
  import numpy as np
  satfunc.df(ResdataFiles('tests/data/reek/eclipse/model/2_R001_REEK-0.DATA')).iloc[np.r_[0:5, 37:42, -5:0]].to_csv('docs/usage/satfunc.csv', index=False)

.. code-block:: python

   from res2df import satfunc, ResdataFiles

   resdatafiles = ResdataFiles('MYDATADECK.DATA')
   dframe = satfunc.df(resdatafiles)

.. csv-table:: Example satfunc table (only a subset of the rows are shown)
   :file: satfunc.csv
   :header-rows: 1

Alternatively, the same data can be produced as a CSV file using the command line

.. code-block:: console

  res2csv satfunc MYDATADECK.DATA --verbose --output satfunc.csv

It is possible to extract keywords one at a time using the ``--keywords`` command
line option.

Instead of complete :term:`decks <deck>`, individual include files may also be parsed, but
only one at a time.

Generating include files from dataframes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When a dataframe of saturation function data is loaded into Python, any operation
may be applied on the data. Simple operations would typically be scaling, perhaps
individual pr. SATNUM. Still, read below on pyscal before embarking on too many
Pandas operations on saturation functions.

An example operation could for example to scale all `KRW` data of the first SATNUM
in the SWOF table, and if `dframe` holds all the data, this can be performed by
the command

.. code-block:: python

   # Build boolean array of which rows in the big dataframe we want to touch:
   rows_to_touch = (dframe["KEYWORD"] == "SWOF") & (dframe["SATNUM"] == 1)
   # Multiplicate these rows by 0.5
   dframe.loc[rows_to_touch, "KRW"] *= 0.5

For a dataframe or a CSV file in the format provided by this module, an
:term:`include file` can be generated either with the Python API
:func:`res2df.satfunc.df2res` function or the command

.. code-block:: console

  csv2res satfunc satfunc.csv --output relperm.inc --keywords SWOF SGOF --verbose

which should give a file ``relperm.inc`` that can be parsed by reservoir simulators. The command
above will only pick the keywords ``SWOF`` and ``SGOF`` (in the case there are
data for more keywords in the dataframe).

There are no automated checks for validity of the dumped :term:`include file <include file>`.

Extracting properties pr. SATNUM
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have an :term:`include file` prepared (from any source), you might need to
determine certain properties like endpoint. If you need to determine for
example "SOWCR" - the largest oil saturation for which oil is immobile,
because you need to avoid SOWCR + SWCR overshooting 1, you can write a code

.. code-block:: python

    from res2df import satfunc

    # Read an include file directly into a DataFrame
    with open("relperm.inc") as f_handle:
        sat_df = satfunc.df(f_handle.read())

    # Write a function that is to operate on each SATNUM:
    def sowcr(df):
        """Determine the largest oil saturation where
        oil relperm is below 1e-7"""
        return 1 - df[df["KROW"] > 1e-7]["SW"].max()

    # Apply that function individually on each SATNUM:
    sat_df.groupby("SATNUM").apply(sowcr)

for an example :term:`include file`, this could result in

.. code-block:: console

    SATNUM
    1    0.15492
    2    0.21002
    3    0.05442
    dtype: float64

The pyscal library
^^^^^^^^^^^^^^^^^^

Manipulation of curve shapes or potentially interpolation between curves is hard
to do directly on the dataframes. Before doing manipulations of dataframes in
``res2df.satfunc``, consider if it is better to implement the manipulations
through the `pyscal <https://equinor.github.io/pyscal/>`_ library.
Pyscal can create curves from parametrizations, and interpolate between curves.

Pyscal can initialize its relperm objects from :term:`include files<include file>`
through the parsing capabilities of res2df.satfunc.

The function ``pyscal.pyscallist.df()`` is analogous to ``res2df.satfunc.df()`` in
what it produces, and the :func:`res2df.satfunc.df2res()` can be used on both
(potentially with some filtering needed.).
