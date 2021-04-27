======================
Contributing to ecl2df
======================

Contributing to ecl2df is easiest on Linux computers. Windows has not been
tested, and for Mac you will have to compile OPM yourself.

Getting started as a developer
------------------------------

The first thing to do, is to create a fork of ecl2df to your personal
github account. Go to https://github.com/equinor/ecl2df and click the Fork
button.

Clone your fork to your local computer:

.. code-block:: console

  git clone git@github.com:<youraccount>/ecl2df
  cd ecl2df

Then add the upstream repository:

.. code-block:: console

  git remote add upstream git@github.com:equinor/ecl2df

This requires a valid login setup with SSH keys for you github account, needed
for write access.

After cloning, you should make a Python virtual environment in which you install
ecl2df and its dependencies. If you want to create a new virtual environment for
ecl2df, you can do something like the following:

.. code-block:: console

  python3 -m venv venv-ecl2df
  source venv-ecl2df/bin/activate

and then run ``pip`` :

.. code-block:: console

  pip install -e .[tests,docs]

to install ecl2df in "edit"-mode together will all dependencies for ecl2df, its
test suite and documentation.

A good start is to verify that all tests pass after having cloned the
repository, which you can do by running:

.. code-block:: console

  pytest


Getting started on Equinor Linux computers
------------------------------------------

On Equinor Linux computers, is is recommended to run with the Komodo
environment, which will provide an analogue to ``virtualenv`` for
making the virtual environment.

The git operations are the same as above.

Follow instructions on https://fmu-docs.equinor.com/docs/komodo/equinor_komodo_usage.html
for activating a Komodo release, and perform the instructions for extending
Komodo in order to prepare for the command:

.. code-block:: console

  pip install -e .[tests,docs]

NB: For every monthly Komodo release, you might have to remake your komodo-venv.

Using ecl2df without OPM
------------------------

OPM is only pip-installable on Linux. To use the non-OPM dependent ecl2df
modules on something else than Linux (but with libecl installed), you should
install all the dependencies (except OPM) using ``pip`` (see ``setup.py`` for
list of dependencies), and then install ecl2df with the ``--no-deps`` option
to ``pip``. After this, the non-OPM dependent modules should work, and others will
fail with import errors.

Development workflow
--------------------

If you have a feature or bugfix, a typical procedure is to:

* Consider writing an issue on https://github.com/equinor/ecl2df/issues describing
  what is not working or what is not present.
* Make a new git branch for your contribution, from an updated master branch.
* Write a test for the feature or a test proving the bug. Verify that ``pytest``
  now fails. Either append to an existing test-file in ``tests/`` or make
  a new file.
* Implement the feature, or fix the bug, and verify that ``pytest`` succeeds.
* Consider if you should write RST documentation in ``docs/`` in addition to
  docstrings.
* Check your code quality with pylint. New code should aim for maximal pylint
  score. Pylint exceptions should only be used when warranted.
* Commit your changes, remember to add any new files.
* Push your branch to your fork on github, and go to github.com/equinor/ecl2df
  and make a pull request from your branch. Link your pull request to any
  relevant issue.
* Fix any errors that pop up from automated checks.
* Wait for or ask for a code review
* Follow up your pull request by merging in changes from the master branch
  as other pull requests are being merged.
* When your PR is ready for merge, it should usually be "squashed" into a single
  commit that is rebased on top of the current master.

Continuous integration
----------------------

A pull request that has been pushed to Github will be subject to automatic
testing, for code style, ``pytest`` and for documentation validity. If your code
does not pass ``black`` or ``flake8`` verification it will fail the CI workflows.

The exact requirements for CI can be deduced from files in ``.github/workflows/``.
The commands in these files can be run manually on your command line, and if
they fail, you will have to fix before pushing your branch.

Some of the requirements can be added to your editor, but you can also integrate
the tool ``pre-commit``  to your cloned copy in order to force certain checks to be
in place before a commit is accepted. Issue the command ``pre-commit install``
in your copy to get started with this.


Writing documentation
---------------------

Write good docstrings for each function, and use Google style for arguments.
See https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html
for specification.

Add RST (reStructuredText) documentation to files in the ``docs/`` directory.

Your RST files must pass validity through the ``rstcheck`` tool. Use ``sphinx``
to build HTML documentation:

.. code-block:: console

  python setup.py build_sphinx

and check the generated HTML visually by running f.ex firefox:

.. code-block:: console

  firefox build/sphinx/html/index.html &
