from pathlib import Path

from setuptools import find_packages, setup

try:
    from sphinx.setup_command import BuildDoc

    cmdclass = {"build_sphinx": BuildDoc}
except ImportError:
    # Skip cmdclass when sphinx is not installed (yet)

    cmdclass = {}

# Read the contents of README.md, for PyPI
LONG_DESCRIPTION = (Path(__file__).parent / "README.md").read_text()

SETUP_REQUIREMENTS = ["setuptools>=28", "setuptools_scm < 6.1"]
REQUIREMENTS = [
    "ecl",
    "numpy",
    "opm>=2020.10.2",  # NB: Pypi versions.
    "pandas",
    "pyarrow",
    "pyyaml>=5.1",
    "treelib",
]

TEST_REQUIREMENTS = Path("test_requirements.txt").read_text().splitlines()

DOCS_REQUIREMENTS = [
    "autoapi",
    "ipython",
    "rstcheck",
    "sphinx",
    "sphinx-argparse",
    "sphinx-autodoc-typehints",
    "sphinx_rtd_theme",
]
EXTRAS_REQUIRE = {
    "tests": TEST_REQUIREMENTS,
    "docs": DOCS_REQUIREMENTS,
    "ert": ["ert>=2.38.0-b5"],
}

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
    package_data={
        "ecl2df": [
            "opmkeywords/*",
            "config_jobs/*",
            "py.typed",
            "svg_color_keyword_names.txt",
        ]
    },
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "csv2ecl=ecl2df.csv2ecl:main",
            "ecl2csv=ecl2df.ecl2csv:main",
            "ecl2arrow=ecl2df.ecl2csv:main",
        ],
        "ert": ["ecl2df_jobs = ecl2df.hook_implementations.jobs"],
    },
    test_suite="tests",
    install_requires=REQUIREMENTS,
    setup_requires=SETUP_REQUIREMENTS,
    extras_require=EXTRAS_REQUIRE,
    python_requires=">=3.8",
)
