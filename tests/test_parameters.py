"""Test module for parameters"""

import json
import yaml
from pathlib import Path

from ecl2df.parameters import load, load_all, find_parameter_files
from ecl2df.eclfiles import EclFiles

TESTDIR = Path(__file__).absolute().parent
DATAFILE = str(TESTDIR / "data/reek/eclipse/model/2_R001_REEK-0.DATA")


def test_parameters():
    """Test import of parameters.txt++"""
    eclfiles = EclFiles(DATAFILE)

    # NB: This test easily fails due to remnants of other test code..
    assert not find_parameter_files(eclfiles)

    parameterstxt = Path(eclfiles.get_path()) / "parameters.txt"
    # If this exists, it is a remnant from test code that has
    # crashed. It should NOT be in git.
    if parameterstxt.is_file():
        parameterstxt.unlink()
    parameterstxt.write_text("FOO 1\nBAR 3", encoding="utf-8")
    assert Path(parameterstxt).is_file()
    param_dict = load(parameterstxt)
    assert "FOO" in param_dict
    assert "BAR" in param_dict

    assert len(find_parameter_files(eclfiles)) == 1
    parameterstxt.unlink()

    parameterstxt = Path(eclfiles.get_path()).parent / "parameters.txt"
    if parameterstxt.is_file():
        parameterstxt.unlink()
    parameterstxt.write_text("FOO 1\nBAR 3\nCONTACT:BARF 2700", encoding="utf-8")
    assert Path(parameterstxt).is_file()
    param_dict = load(parameterstxt)
    assert "FOO" in param_dict
    assert "BAR" in param_dict
    assert param_dict["BAR"] == 3
    assert param_dict["CONTACT:BARF"] == 2700
    assert len(find_parameter_files(eclfiles)) == 1
    parameterstxt.unlink()

    # Typical parameters.json structure: The group "CONTACT" is assumed having
    # duplicate information, and is to be ignored
    dump_me = {"FOO": 1, "BAR": "com", "CONTACT:BARF": 2700, "CONTACT": {"BARF": 2700}}

    parametersyml = Path(eclfiles.get_path()) / "parameters.yml"
    if parametersyml.is_file():
        parametersyml.unlink()
    parametersyml.write_text(yaml.dump(dump_me), encoding="utf-8")
    assert Path(parametersyml).is_file()
    assert len(find_parameter_files(eclfiles)) == 1
    param_dict = load(parametersyml)
    assert "FOO" in param_dict
    assert "BAR" in param_dict
    assert param_dict["BAR"] == "com"
    parametersyml.unlink()

    parametersjson = Path(eclfiles.get_path()) / "parameters.json"
    if parametersjson.is_file():
        parametersjson.unlink()
    parametersjson.write_text(json.dumps(dump_me), encoding="utf-8")
    assert Path(parametersjson).is_file()
    assert len(find_parameter_files(eclfiles)) == 1
    param_dict = load(find_parameter_files(eclfiles)[0])
    param_dict_m = load_all(find_parameter_files(eclfiles))
    assert "FOO" in param_dict
    assert "BAR" in param_dict
    assert param_dict["BAR"] == "com"
    assert param_dict == param_dict_m
    parametersjson.unlink()


def test_multiple_parameters():
    """Test what happens when we have duplicate parameter files"""
    eclfiles = EclFiles(DATAFILE)
    parametersjson = Path(eclfiles.get_path()) / "parameters.json"
    parameterstxt = Path(eclfiles.get_path()).parent / "parameters.txt"
    parameterstxt.write_text("FOO 1\nBAR 4", encoding="utf-8")
    parametersjson.write_text(json.dumps({"BAR": 5, "COM": 6}), encoding="utf-8")
    param_dict = load_all(find_parameter_files(eclfiles))
    assert len(param_dict) == 3
    assert param_dict["BAR"] == 5  # json has precedence over txt
    parametersjson.unlink()
    parameterstxt.unlink()
