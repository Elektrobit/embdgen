from io import BytesIO
import pytest
from pathlib import Path

from embdgen.plugins.content.UBootEnvContent import UBootEnvContent
from embdgen.core.utils.SizeType import SizeType

class TestUBootEnvContent:
    def test_assign_invalid_file(self):
        with pytest.raises(Exception, match="File /path/i-do-not-exist does not exist"):
            UBootEnvContent().file = Path("/path/i-do-not-exist")

    def test_no_size(self):
        obj = UBootEnvContent()
        with pytest.raises(Exception, match="Size for U-Boot environment must be defined"):
            obj.prepare()

    def test_empty(self):
        obj = UBootEnvContent()
        obj.size = SizeType(1024)
        obj.prepare()

        img = BytesIO()
        obj.write(img)
        buf = img.getbuffer()
        assert buf == b"\x97\xdb\x74\x10" + b"\0" + b"\xff" * 1019

    def test_file(self, tmp_path: Path):
        uboot_env = tmp_path / "uboot.env"
        uboot_env.write_text(
            """
            C=D
            A=B
            #D=E
            Empty=
            A=Some other string with spaces
            """.strip()
        )
        obj = UBootEnvContent()
        obj.file = uboot_env
        obj.size = SizeType(1024)
        obj.prepare()
        img = BytesIO()
        obj.write(img)
        buf = img.getbuffer()
        data = b"A=Some other string with spaces\0C=D\0Empty=\0\0"
        assert buf == b"\x08\x88\x28\xfa" + data + b"\xff" * (1024 - 4 - len(data))

    def test_file_invalid_line(self, tmp_path: Path):
        uboot_env = tmp_path / "uboot.env"
        uboot_env.write_text(
            """
            C=D
            A
            #D=E
            A=Some other string with spaces
            """.strip()
        )
        obj = UBootEnvContent()
        obj.file = uboot_env
        obj.size = SizeType(1024)
        with pytest.raises(Exception, match=r"Invalid entry in U-Boot environment file \(line 2\)"):
            obj.prepare()

    def test_vars(self):
        obj = UBootEnvContent()
        obj.vars = {
            "C": "D",
            "A": "Some other string with spaces",
            "Empty": ""
        }
        obj.size = SizeType(1024)
        obj.prepare()
        img = BytesIO()
        obj.write(img)
        buf = img.getbuffer()
        data = b"A=Some other string with spaces\0C=D\0Empty=\0\0"
        assert buf == b"\x08\x88\x28\xfa" + data + b"\xff" * (1024 - 4 - len(data))

    def test_file_and_vars(self, tmp_path: Path):
        uboot_env = tmp_path / "uboot.env"
        uboot_env.write_text(
            """
            C=D
            Some Var = I will be overwritten by vars
            """.strip()
        )
        obj = UBootEnvContent()
        obj.file = uboot_env
        obj.vars = {
            "Some Var": "I overwrite var A from file",
            "NewVar": "Additional var in vars"
        }
        obj.size = SizeType(1024)
        obj.prepare()
        img = BytesIO()
        obj.write(img)
        buf: memoryview = img.getbuffer()
        data = b"C=D\0NewVar=Additional var in vars\0Some Var=I overwrite var A from file\0\0"
        assert buf == b"\x9f\xac\xf1\xb0" + data + b"\xff" * (1024 - 4 - len(data))

    def test_overflow(self):
        obj = UBootEnvContent()
        obj.size = SizeType(100)
        obj.vars = {
            "A": "x" * (100 - 4 - len(b"A=\0\0"))
        }
        obj.prepare()

        obj.vars = {
            "A": "x" * (100 - 4 - len(b"A=\0\0") + 1)
        }
        with pytest.raises(Exception, match=r"U-Boot environment variables overflow storage area by 1 byte"):
            obj.prepare()

        obj.vars = {
            "A": "x" * (100 - 4 - len(b"A=\0\0") + 548)
        }
        with pytest.raises(Exception, match=r"U-Boot environment variables overflow storage area by 548 byte"):
            obj.prepare()
