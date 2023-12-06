gruptree
--------

Extracts data from the GRUPTREE, GRUPNET and WELSPECS keywords from a :term:`.DATA file`
and presents the production network either as pretty-printed ASCII or in a
dataframe-representation.

The GRUPTREE section of your :term:`.DATA file` defines the production network
from wells and up to the platform (and possibly also to a field having
many platforms). In the :term:`.DATA file` it be as simple as this::

    START
      01 'JAN' 2000 /

    SCHEDULE

    GRUPTREE
      'OPEAST' 'OP' /
      'OPWEST' 'OP' /
      'INJEAST' 'WI' /
      'OP' 'FIELD' /
      'WI' 'FIELD' /
      'FIELD' 'AREA' /
      'AREA' 'NORTHSEA' /
    /

which will yield the dataframe

.. csv-table:: GRUPTREE as a dataframe
   :file: gruptree.csv
   :header-rows: 1

If you run this from the command line, a pretty printed ASCII graph is also
available (here also wells from WELSPECS is included):

.. code-block:: console

    > res2csv gruptree --prettyprint MYDATADECK.DATA
    Date: 2000-01-01
    └── NORTHSEA
        └── AREA
            └── FIELD
                ├── OP
                │   ├── OPEAST
                │   │   └── OP2
                │   └── OPWEST
                │       └── OP1
                └── WI
                    └── INJEAST
                        └── INJ1

In your :term:`deck`, the table will be repeated for every new occurence of the
GRUPTREE keyword in the Schedule section.

GRUPNET and WELSPECS
~~~~~~~~~~~~~~~~~~~~

By default, the module will also pick up information from GRUPNET (typical
terminal pressure values for the network nodes) and WELSPECS (well
specifications), so for a full :term:`deck`, your dataframe will contain more
information than in the example above.

If our :term:`deck` also contains::

    GRUPNET
      'FIELD' 90 /
      'OPWEST' 100 /
    /

    WELSPECS
      'OP1'  'OPWEST'  41 125 1759.74 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
      'OP2'  'OPEAST'  43 122 1776.01 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
      'INJ1' 'INJEAST' 33 115 1960.21 'OIL' 0.0 'STD' 'SHUT' 'YES'  0  'SEG' /
    /

the dataframe will get additional rows and columns:

.. csv-table:: Dataframe from GRUPTREE, GRUPNET and WELSPECS
   :file: gruptreenet.csv
   :header-rows: 1

