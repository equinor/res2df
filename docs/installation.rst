Installation
============

Internally in Equinor, ecl2df is distributed through Komodo and
nothing is needed besides activating Komodo, typically through one of the
commands::

  source /prog/res/komodo/stable/enable.csh  # csh shell
  source /prog/res/komodo/stable/enable  # bash shell

On Linux computers outside Equinor, ecl2df should be installed from
https://pypi.org:

.. code-block:: console

  pip install ecl2df

For MacOS, the OPM dependency is not available from pypi, and OPM must be
compiled manually.
