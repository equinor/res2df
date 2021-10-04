"""Test module for parameters"""

import json
import os
from pathlib import Path

import pytest
import yaml

from ecl2df.eclfiles import EclFiles
from ecl2df.parameters import find_parameter_files, load, load_all

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


def test_find_parameter_files_modeldir(tmp_path):
    """Test find_parameter_files when parameters are in the model directory."""
    os.chdir(tmp_path)
    model_dir = Path("realization-0/iter-0/eclipse/model")
    model_dir.mkdir(parents=True)
    assert find_parameter_files(model_dir / "FOO.DATA") == []
    (model_dir / "parameters.txt").touch()
    assert find_parameter_files(model_dir / "FOO.DATA") == [
        model_dir.absolute() / "parameters.txt"
    ]

    # yml are preferred over txt:
    (model_dir / "parameters.yml").touch()
    assert find_parameter_files(model_dir / "FOO.DATA") == [
        model_dir.absolute() / "parameters.yml",
        model_dir.absolute() / "parameters.txt",
    ]

    # json is preferred over yml again:
    (model_dir / "parameters.json").touch()
    assert find_parameter_files(model_dir / "FOO.DATA") == [
        model_dir.absolute() / "parameters.json",
        model_dir.absolute() / "parameters.yml",
        model_dir.absolute() / "parameters.txt",
    ]

    # Changing filebase:
    assert find_parameter_files(model_dir / "FOO.DATA", filebase="foo") == []
    (model_dir / "foo.yml").touch()
    assert find_parameter_files(model_dir / "FOO.DATA", filebase="foo") == [
        model_dir.absolute() / "foo.yml"
    ]

    with pytest.raises(TypeError):
        find_parameter_files({"foo": "bar"})


def test_find_parameter_files_verticalplacement(tmp_path):
    """Test find_parameter_files with parameters.txt placed above in the hiearchy."""
    os.chdir(tmp_path)
    model_dir = Path("foo/bar/realization-0/iter-0/eclipse/model")
    model_dir.mkdir(parents=True)

    # Too shallow parameters.txt is not found:
    (model_dir.parent.parent.parent / "parameters.txt").touch()
    assert find_parameter_files(model_dir / "FOO.DATA") == []

    # Two levels (realization-level) is found:
    (model_dir.parent.parent / "parameters.txt").touch()
    assert find_parameter_files(model_dir / "FOO.DATA") == [
        model_dir.absolute().parent.parent / "parameters.txt"
    ]

    # One level up is found:
    (model_dir.parent.parent / "parameters.txt").unlink()
    (model_dir.parent / "parameters.txt").touch()
    assert find_parameter_files(model_dir / "FOO.DATA") == [
        model_dir.absolute().parent / "parameters.txt"
    ]

    # If found both places, deepest location is preferred:
    (model_dir.parent.parent / "parameters.txt").touch()
    (model_dir.parent / "parameters.txt").touch()
    assert find_parameter_files(model_dir / "FOO.DATA") == [
        model_dir.absolute().parent / "parameters.txt",
        model_dir.absolute().parent.parent / "parameters.txt",
    ]


def test_load(tmp_path):
    """Test loading of yml/json/txt files into dictionaries"""
    os.chdir(tmp_path)

    Path("empty").touch()
    assert load("empty") == {}  # A warning is logged

    # yaml file:
    Path("foo.yml").write_text("foo: bar")
    assert load("foo.yml") == {"foo": "bar"}
    assert load(Path("foo.yml")) == {"foo": "bar"}

    # yaml syntax errors:
    Path("error.yml").write_text("foo: bar :")
    with pytest.raises(ValueError, match="Could not parse error.yml"):
        load("error.yml")

    # json file:
    Path("foo.json").write_text('{\n  "foo": "bar"\n}')
    assert load("foo.json") == {"foo": "bar"}

    # Extension does not matter:
    Path("wrongextension.yml").write_text('{\n  "foo": "bar"\n}')
    assert load("wrongextension.yml") == {"foo": "bar"}

    # txt file:
    Path("foo.txt").write_text("foo bar")
    assert load("foo.txt") == {"foo": "bar"}

    # txt file errors:
    Path("error.txt").write_text("foo bar com")
    with pytest.raises(ValueError, match="Could not parse error.txt"):
        load("error.txt") == {"foo": "bar"}

    with pytest.raises(FileNotFoundError, match="notexisting not found"):
        load("notexisting")
