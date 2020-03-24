# -*- coding: utf-8 -*-
from setuptools import setup
from setuptools_scm import get_version
from sphinx.setup_command import BuildDoc


def parse_requirements(filename):
    """Load requirements from a pip requirements file"""
    try:
        lineiter = (line.strip() for line in open(filename))
        return [line for line in lineiter if line and not line.startswith("#")]
    except IOError:
        return []


REQUIREMENTS = parse_requirements("requirements.txt")
TEST_REQUIREMENTS = parse_requirements("requirements_dev.txt")
SETUP_REQUIREMENTS = ["pytest-runner", "setuptools >=28", "setuptools_scm"]

setup(
    name="ecl2df",
    use_scm_version={"write_to": "ecl2df/version.py"},
    cmdclass={"build_sphinx": BuildDoc},
    description="Convert Eclipse 100 input and output to DataFrames",
    url="http://github.com/equinor/ecl2df",
    author="Håvard Berland",
    author_email="havb@equinor.com",
    license="GPLv3",
    packages=["ecl2df"],
    package_dir={"ecl2df": "ecl2df"},
    package_data={"ecl2df": ["opmkeywords/*"]},
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "ecl2csv=ecl2df.ecl2csv:main",
            "nnc2csv=ecl2df.nnc:main",
            "eclgrid2csv=ecl2df.grid:main",
            "grid2csv=ecl2df.grid:main",
            "summary2csv=ecl2df.summary:main",
            "rft2csv=ecl2df.rft:main",
            "compdat2csv=ecl2df.compdat:main",
            "equil2csv=ecl2df.equil:main",
            "gruptree2csv=ecl2df.gruptree:main",
            "satfunc2csv=ecl2df.satfunc:main",
            "trans2csv=ecl2df.trans:main",
            "faults2csv=ecl2df.faults:main",
            "wcon2csv=ecl2df.wcon:main",
        ]
    },
    install_requires=REQUIREMENTS,
    tests_require=TEST_REQUIREMENTS,
    setup_requires=SETUP_REQUIREMENTS,
)
