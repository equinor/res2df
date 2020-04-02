"""Test module for parameters"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os

import json
import yaml

from ecl2df.parameters import load, load_all, find_parameter_files
from ecl2df.eclfiles import EclFiles

TESTDIR = os.path.dirname(os.path.abspath(__file__))
DATAFILE = os.path.join(TESTDIR, "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_parameters():
    """Test import of parameters.txt++"""
    eclfiles = EclFiles(DATAFILE)

    # NB: This test easily fails due to remnants of other test code..
    assert not find_parameter_files(eclfiles)

    parameterstxt = os.path.join(eclfiles.get_path(), "parameters.txt")
    if os.path.exists(parameterstxt):
        # If this exists, it is a remnant from test code that has
        # crashed. It should NOT be in git.
        os.unlink(parameterstxt)
    with open(parameterstxt, "w") as pfile:
        pfile.write("FOO 1\nBAR 3")
    assert os.path.exists(parameterstxt)
    param_dict = load(parameterstxt)
    assert "FOO" in param_dict
    assert "BAR" in param_dict

    assert len(find_parameter_files(eclfiles)) == 1
    os.unlink(parameterstxt)

    parameterstxt = os.path.join(eclfiles.get_path(), os.pardir, "parameters.txt")
    if os.path.exists(parameterstxt):
        os.unlink(parameterstxt)
    with open(parameterstxt, "w") as pfile:
        pfile.write("FOO 1\nBAR 3\n")
        pfile.write("CONTACT:BARF 2700")
    assert os.path.exists(parameterstxt)
    param_dict = load(parameterstxt)
    assert "FOO" in param_dict
    assert "BAR" in param_dict
    assert param_dict["BAR"] == 3
    assert param_dict["CONTACT:BARF"] == 2700
    assert len(find_parameter_files(eclfiles)) == 1
    os.unlink(parameterstxt)

    # Typical parameters.json structure: The group "CONTACT" is assumed having
    # duplicate information, and is to be ignored
    dump_me = {"FOO": 1, "BAR": "com", "CONTACT:BARF": 2700, "CONTACT": {"BARF": 2700}}

    parametersyml = os.path.join(eclfiles.get_path(), "parameters.yml")
    if os.path.exists(parametersyml):
        os.unlink(parametersyml)
    with open(parametersyml, "w") as pfile:
        pfile.write(yaml.dump(dump_me))
    assert os.path.exists(parametersyml)
    assert len(find_parameter_files(eclfiles)) == 1
    param_dict = load(parametersyml)
    assert "FOO" in param_dict
    assert "BAR" in param_dict
    assert param_dict["BAR"] == "com"
    os.unlink(parametersyml)

    parametersjson = os.path.join(eclfiles.get_path(), "parameters.json")
    if os.path.exists(parametersjson):
        os.unlink(parametersjson)
    with open(parametersjson, "w") as pfile:
        pfile.write(json.dumps(dump_me))
    assert os.path.exists(parametersjson)
    assert len(find_parameter_files(eclfiles)) == 1
    param_dict = load(find_parameter_files(eclfiles)[0])
    param_dict_m = load_all(find_parameter_files(eclfiles))
    assert "FOO" in param_dict
    assert "BAR" in param_dict
    assert param_dict["BAR"] == "com"
    assert param_dict == param_dict_m
    os.unlink(parametersjson)


def test_multiple_parameters():
    """Test what happens when we have duplicate parameter files"""
    eclfiles = EclFiles(DATAFILE)
    parametersjson = os.path.join(eclfiles.get_path(), "parameters.json")
    parameterstxt = os.path.join(eclfiles.get_path(), os.pardir, "parameters.txt")
    with open(parameterstxt, "w") as pfile:
        pfile.write("FOO 1\nBAR 4")
    with open(parametersjson, "w") as pfile:
        pfile.write(json.dumps({"BAR": 5, "COM": 6}))
    param_dict = load_all(find_parameter_files(eclfiles))
    assert len(param_dict) == 3
    assert param_dict["BAR"] == 5  # json has precedence over txt
    os.unlink(parametersjson)
    os.unlink(parameterstxt)
