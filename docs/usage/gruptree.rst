gruptree
--------

Extracts data from the GRUPTREE, GRUPNET and WELSPECS keywords from an Eclipse
deck and presents the production network either as pretty-printed ASCII, in a
dataframe-representation or as a `networx <https://networkx.github.io/>` graph.

The GRUPTREE section of your Eclipse deck defines the production network
from wells and up to the platform (and possibly also to a field having
many platforms). In the Eclipse deck it be as simple as this::

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


