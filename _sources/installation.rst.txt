Installation
============

Internally in Equinor, ecl2df is distributed through Komodo.

You need opm-common installed upfront.

Either install a released version from pypi by

.. code-block:: console

    > pip install ecl2df

or install the latest development version from source by the commands

.. code-block:: console

    > git clone https://github.com/equinor/ecl2df
    > cd ecl2df
    > pip install -r requirements.txt
    > pip install -e .

For the opm-common installation, you can get hints from the
file `.travis.yml <https://github.com/equinor/ecl2df/blob/master/.travis.yml>`_
in the ecl2df repository. This describes a working installation for a given
Linux release, but it might require some adjustments on other systems.
