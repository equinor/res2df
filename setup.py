from setuptools import setup

setup(
    name="ecl2df",
    version="0.0.1",
    description="Convert Eclipse 100 input and output to DataFrames",
    url="http://github.com/equinor/ecl2df",
    author="Håvard Berland",
    author_email="havb@equinor.com",
    license="LGPLv3",
    packages=["ecl2df"],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "nnc2csv=ecl2df.nnc2df:main",
            "eclgrid2csv=ecl2df.grid2df:main",
            "grid2csv=ecl2df.grid2df:main",
            "summary2csv=ecl2df.summary2df:main",
            "rft2csv=ecl2df.rft2df:main",
            "compdat2csv=ecl2df.compdat2df:main",
        ]
    },
)
