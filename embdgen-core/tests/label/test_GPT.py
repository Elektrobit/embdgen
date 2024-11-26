# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import pytest

from embdgen.core.utils.image import BuildLocation
from embdgen.core.utils.SizeType import SizeType

from embdgen.plugins.label.GPT import GPT
from embdgen.plugins.region.EmptyRegion import EmptyRegion
from embdgen.plugins.region.PartitionRegion import PartitionRegion
from embdgen.plugins.content.EmptyContent import EmptyContent

from embdgen.plugins.region.RawRegion import RawRegion
from embdgen.plugins.content.RawContent import RawContent
from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.plugins.content.Fat32Content import Fat32Content

from ..test_utils.FdiskParser import FdiskParser, FdiskRegion

class TestGPT:
    def test_withParts(self, tmp_path):
        BuildLocation().set_path(tmp_path)

        image = tmp_path / "image"
        obj = GPT()

        empty = EmptyRegion()
        empty.name = "empty region"
        empty.start = SizeType(512 * 34)
        empty.size = SizeType(512)

        ext4_raw = tmp_path / "ext4"
        ext4_raw.write_bytes(b"1" * 512 * 2)
        ext4 = PartitionRegion()
        ext4.fstype = "ext4"
        ext4.name = "ext4 region"
        ext4.content = RawContent()
        ext4.content.file = ext4_raw

        fat32 = PartitionRegion()
        fat32.fstype = "fat32"
        fat32.name = "fat32 region"
        fat32.content = Fat32Content()
        fat32.content.content = FilesContent()
        fat32.size = SizeType.parse("5MB")

        obj.parts = [
            empty,
            ext4,
            fat32
        ]
        obj.boot_partition = ext4.name

        obj.prepare()

        obj.create(image)

        fdisk = FdiskParser(image)

        assert fdisk.is_valid
        assert len(fdisk.regions) == 2
        assert fdisk.regions[0].start_sector == 35
        assert fdisk.regions[1].start_sector == 37

    def test_overlap_GPT_header(self):
        obj = GPT()

        empty = EmptyRegion()
        empty.name = "empty region"
        empty.start = SizeType(512)
        empty.size = SizeType(512)

        obj.parts.append(empty)

        with pytest.raises(Exception, match="Part 'empty region' overlapps with 'GPT Header'"):
            obj.prepare()

    def test_overlap_GPT_table(self, tmp_path, capsys: pytest.CaptureFixture[str]):
        BuildLocation().set_path(tmp_path)

        image = tmp_path / "image"
        obj = GPT()

        empty = EmptyRegion()
        empty.name = "empty region"
        empty.start = SizeType(512 * 2)
        empty.size = SizeType(512)

        obj.parts.append(empty)

        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)

        assert fdisk.is_valid

        output = capsys.readouterr().out
        assert output == "The location for the GPT Partition Table is used by another region. Table will be relocated\n"

    def test_overlap_GPT_table_withParts(self, tmp_path, capsys: pytest.CaptureFixture[str]):
        BuildLocation().set_path(tmp_path)

        image = tmp_path / "image"
        obj = GPT()

        empty = EmptyRegion()
        empty.name = "empty region"
        empty.start = SizeType(512 * 2)
        empty.size = SizeType(512)

        ext4_raw = tmp_path / "ext4"
        ext4_raw.write_bytes(b"1" * 512 * 2)
        ext4 = PartitionRegion()
        ext4.fstype = "ext4"
        ext4.name = "ext4 region"
        ext4.content = RawContent()
        ext4.content.file = ext4_raw

        fat32 = PartitionRegion()
        fat32.fstype = "fat32"
        fat32.name = "fat32 region"
        fat32.content = Fat32Content()
        fat32.content.content = FilesContent()
        fat32.size = SizeType.parse("5MB")

        obj.parts = [
            empty,
            ext4,
            fat32
        ]
        obj.boot_partition = ext4.name

        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)

        assert fdisk.is_valid
        assert len(fdisk.regions) == 2
        assert fdisk.regions[0].start_sector == 35
        assert fdisk.regions[1].start_sector == 37
        output = capsys.readouterr().out
        assert output == "The location for the GPT Partition Table is used by another region. Table will be relocated\n"


    def test_overlap_check_data_integrity(self, tmp_path, capsys: pytest.CaptureFixture[str]):
        BuildLocation().set_path(tmp_path)

        image = tmp_path / "image"
        obj = GPT()

        rawDataFile = tmp_path / "rawData"
        rawDataFile.write_bytes(b"TEST" * 512)
        rawData = RawRegion()
        rawData.content = RawContent()
        rawData.content.file = rawDataFile
        rawData.start = SizeType(512 * 2)
        rawData.size = SizeType(512 * 4)
        rawData.name = "RawData"

        obj.parts.append(rawData)

        fat32 = PartitionRegion()
        fat32.fstype = "fat32"
        fat32.name = "fat32 region"
        fat32.content = Fat32Content()
        fat32.content.content = FilesContent()
        fat32.size = SizeType.parse("5MB")

        obj.parts.append(fat32)

        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)

        assert fdisk.is_valid
        output = image.read_bytes()
        output_w_offset = output[rawData.start.bytes:rawData.start.bytes + 512 * 4]
        assert output_w_offset == (b"TEST" * 512)
        output = capsys.readouterr().out
        assert output == "The location for the GPT Partition Table is used by another region. Table will be relocated\n"


    def test_overlap_unaligned_region(self, tmp_path, capsys: pytest.CaptureFixture[str]):
        BuildLocation().set_path(tmp_path)

        image = tmp_path / "image"
        obj = GPT()

        rawDataFile = tmp_path / "rawData"
        testStrLen = 32
        rawDataFile.write_bytes(b"TEST" * testStrLen)
        rawData = RawRegion()
        rawData.content = RawContent()
        rawData.content.file = rawDataFile
        rawData.start = SizeType(512 * 2 + 64)
        rawData.size = SizeType(testStrLen * 4)
        rawData.name = "RawData"

        obj.parts.append(rawData)

        fat32 = PartitionRegion()
        fat32.fstype = "fat32"
        fat32.name = "fat32 region"
        fat32.content = Fat32Content()
        fat32.content.content = FilesContent()
        fat32.size = SizeType.parse("5MB")

        obj.parts.append(fat32)

        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)

        assert fdisk.is_valid
        output = image.read_bytes()
        output_w_offset = output[rawData.start.bytes : rawData.start.bytes + testStrLen * 4]
        assert output_w_offset == (b"TEST" * testStrLen)
        output = capsys.readouterr().out
        assert output == "The location for the GPT Partition Table is used by another region. Table will be relocated\n"

    def test_overlap_multiRegion(self, tmp_path, capsys: pytest.CaptureFixture[str]):
        BuildLocation().set_path(tmp_path)

        image = tmp_path / "image"
        obj = GPT()

        rawDataFile1 = tmp_path / "rawData1"
        rawDataFile1.write_bytes(b"TEST" * 512)
        rawData1 = RawRegion()
        rawData1.content = RawContent()
        rawData1.content.file = rawDataFile1
        rawData1.start = SizeType(512 * 2)
        rawData1.size = SizeType(512 * 4)
        rawData1.name = "RawData_1"

        obj.parts.append(rawData1)

        rawDataFile2 = tmp_path / "rawData2"
        rawDataFile2.write_bytes(b"DATA" * 512)
        rawData2 = RawRegion()
        rawData2.content = RawContent()
        rawData2.content.file = rawDataFile2
        rawData2.start = SizeType(512 * 10)
        rawData2.size = SizeType(512 * 4)
        rawData2.name = "RawData_2"

        obj.parts.append(rawData2)

        fat32 = PartitionRegion()
        fat32.fstype = "fat32"
        fat32.name = "fat32 region"
        fat32.content = Fat32Content()
        fat32.content.content = FilesContent()
        fat32.size = SizeType.parse("5MB")

        obj.parts.append(fat32)

        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)

        assert fdisk.is_valid
        output = image.read_bytes()
        output_w_offset = output[rawData1.start.bytes : rawData1.start.bytes + 512 * 4]
        assert output_w_offset == (b"TEST" * 512)
        output_w_offset_2 = output[rawData2.start.bytes : rawData2.start.bytes + 512 * 4]
        assert output_w_offset_2 == (b"DATA" * 512)
        output = capsys.readouterr().out
        assert output == "The location for the GPT Partition Table is used by another region. Table will be relocated\n"
