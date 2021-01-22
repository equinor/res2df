from os import path

from setuptools import setup, find_packages

try:
    from sphinx.setup_command import BuildDoc

    cmdclass = {"build_sphinx": BuildDoc}
except ImportError:
    # Skip cmdclass when sphinx is not installed (yet)

    cmdclass = {}

# Read the contents of README.md, for PyPI
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md")) as f_handle:
    LONG_DESCRIPTION = f_handle.read()

SETUP_REQUIREMENTS = ["setuptools>=28", "setuptools_scm"]
REQUIREMENTS = [
    "ecl",
    "equinor-libres",
    "ert",
    "numpy",
    "opm>=2020.10.2",  # NB: Pypi versions.
    "pandas",
    "pyyaml>=5.1",
    "treelib",
]
TEST_REQUIREMENTS = [
    "black>=20.8b0",
    "flake8",
    "networkx",
    "pre-commit",
    "pytest",
    "pytest-cov",
    "pytest-mock",
]

DOCS_REQUIREMENTS = [
    "ipython",
    "rstcheck",
    "sphinx",
    "sphinx-argparse",
    "sphinx_rtd_theme",
]
EXTRAS_REQUIRE = {"tests": TEST_REQUIREMENTS, "docs": DOCS_REQUIREMENTS}

setup(
    name="ecl2df",
    use_scm_version={"write_to": "ecl2df/version.py"},
    cmdclass=cmdclass,
    description="Convert Eclipse 100 input and output to DataFrames",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="http://github.com/equinor/ecl2df",
    author="Håvard Berland",
    author_email="havb@equinor.com",
    license="GPLv3",
    packages=find_packages(include=["ecl2df*"]),
    package_dir={"ecl2df": "ecl2df"},
    package_data={"ecl2df": ["opmkeywords/*", "config_jobs/*"]},
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "csv2ecl=ecl2df.csv2ecl:main",
            "ecl2csv=ecl2df.ecl2csv:main",
        ],
        "ert": ["ecl2df_jobs = ecl2df.hook_implementations.jobs"],
    },
    test_suite="tests",
    install_requires=REQUIREMENTS,
    setup_requires=SETUP_REQUIREMENTS,
    extras_require=EXTRAS_REQUIRE,
    python_requires=">=3.6",
)
