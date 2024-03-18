# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import pytest
from pytest_mock import MockerFixture
from embdgen.core.cli import cli

from embdgen.core.config.Factory import Factory
from embdgen.core.config.BaseConfig import BaseConfig
from embdgen.plugins.label.MBR import MBR

Factory() # Instantiate to load class variables

class TestConfig(BaseConfig):
    def load(self, filename: Path):
        return MBR()

    def load_str(self, data: str):
        return MBR()

    @classmethod
    def probe(cls, _filename: Path) -> bool:
        return True

class TestConfig2(BaseConfig):
    was_called = False
    def load(self, filename: Path):
        self.__class__.was_called = True
        return MBR()

    def load_str(self, data: str):
        self.__class__.was_called = True
        return MBR()

    @classmethod
    def probe(cls, _filename: Path) -> bool:
        return False

def test_no_arguments(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit, match="2"):
        cli([])
    output = capsys.readouterr().err
    assert output.startswith("usage:")

def test_nonexisting_file():
    with pytest.raises(SystemExit, match="FATAL: The config file i-do-not-exist does not exist"):
        cli(['i-do-not-exist'])

def test_valid_file_no_matcher():
    with pytest.raises(SystemExit, match="FATAL: Unable to detect the format of the config file"):
        cli([
            str(Path(__file__).parent / "data/config.cfg")
        ])

def test_invalid_format(capsys: pytest.CaptureFixture[str]):
    with pytest.raises(SystemExit, match="2"):
        cli([
            "--format", "invalid",
            str(Path(__file__).parent / "data/config.cfg")
        ])
    output = capsys.readouterr().err
    assert output.startswith("usage:")

def test_no_match(mocker: MockerFixture, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    output_file = tmp_path / "image"
    tmp_dir = tmp_path / "tmp"
    mocker.patch.dict(Factory.class_map(), {'test2': TestConfig2}, clear=True)

    with pytest.raises(SystemExit, match="Unable to detect the format of the config file"):
        cli([
            "--output", str(output_file),
            "--tempdir", str(tmp_dir),
            str(Path(__file__).parent / "data/config.cfg")
        ])

def test_complete(mocker: MockerFixture, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    output_file = tmp_path / "image"
    tmp_dir = tmp_path / "tmp"
    mocker.patch.dict(Factory.class_map(), {'test': TestConfig, 'test2': TestConfig2}, clear=True)

    cli([
        "--output", str(output_file),
        "--tempdir", str(tmp_dir),
        str(Path(__file__).parent / "data/config.cfg")
    ])

    assert output_file.exists()
    assert not tmp_dir.exists()

    capsys.readouterr() # suppress output

def test_complete_explit_format(mocker: MockerFixture, capsys: pytest.CaptureFixture[str], tmp_path: Path):
    mocker.patch.dict(Factory.class_map(), {'test': TestConfig, 'test2': TestConfig2}, clear=True)

    output_file = tmp_path / "image"
    tmp_dir = tmp_path / "tmp"

    TestConfig2.was_called = False
    cli([
        "--output", str(output_file),
        "--tempdir", str(tmp_dir),
        "--format", "test2",
        str(Path(__file__).parent / "data/config.cfg")
    ])

    assert TestConfig2.was_called
    assert output_file.exists()
    assert not tmp_dir.exists()

    capsys.readouterr() # suppress output
