# SPDX-License-Identifier: GPL-3.0-only

from typing import List
import re
import subprocess
from dataclasses import dataclass
import pytest

from embdgen.core.utils.image import get_temp_path
from embdgen.core.utils.SizeType import SizeType

from embdgen.plugins.label.GPT import GPT
from embdgen.plugins.region.EmptyRegion import EmptyRegion
from embdgen.plugins.region.PartitionRegion import PartitionRegion

from embdgen.plugins.content.RawContent import RawContent
from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.plugins.content.Fat32Content import Fat32Content

@dataclass
class FdiskRegion:
    start_sector: int
    end_sector: int
    sectors: int


class FdiskParser:
    is_valid: bool = False
    regions: List[FdiskRegion]

    def __init__(self, image):
        self.regions = []
        ret = subprocess.run([
            'fdisk',
            '-l',
            image
        ], stdout=subprocess.PIPE, check=False, encoding="ascii")
        if ret.returncode == 0:
            self.is_valid = True
        self._parse(ret.stdout)

    def _parse(self, output: str):
        """
        Units: sectors of 1 * 512 = 512 bytes
        Sector size (logical/physical): 512 bytes / 512 bytes
        I/O size (minimum/optimal): 512 bytes / 512 bytes
        Disklabel type: gpt
        Disk identifier: 5C51AF51-0A45-4144-A6EC-A2DA8B6317D5

        Device     Start   End Sectors Size Type
        image.raw1  3856  5903    2048   1M EFI System
        image.raw2  5904 16143   10240   5M Microsoft basic data


        """
        in_regions = False
        for line in output.splitlines():
            if in_regions:
                parts = re.split(r"\s+", line)
                _, start, end, sectors, _, *_ = parts
                self.regions.append(FdiskRegion(
                    int(start),
                    int(end),
                    int(sectors),
                ))

            else:
                if line.startswith("Disk identifier:"):
                    self.diskid = int((line.split(":")[1]).split("-")[0], 16)
                elif line.startswith("Device"):
                    in_regions = True




class TestGPT:
    def test_withParts(self, tmp_path):
        get_temp_path.TEMP_PATH = tmp_path
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


    def test_overlap_primary(self):
        obj = GPT()

        empty = EmptyRegion()
        empty.name = "empty region"
        empty.start = SizeType(512 * 33)
        empty.size = SizeType(512)

        obj.parts.append(empty)

        with pytest.raises(Exception, match="Part 'empty region' overlapps with 'GPT Header'"):
            obj.prepare()
