# SPDX-License-Identifier: GPL-3.0-only

from typing import List
import re
from pathlib import Path
import subprocess
from dataclasses import dataclass

from embdgen.core.utils.image import BuildLocation
from embdgen.core.utils.SizeType import SizeType

from embdgen.plugins.label.MBR import MBR
from embdgen.plugins.region.EmptyRegion import EmptyRegion
from embdgen.plugins.region.PartitionRegion import PartitionRegion
from embdgen.plugins.region.RawRegion import RawRegion

from embdgen.plugins.content.RawContent import RawContent
from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.plugins.content.Fat32Content import Fat32Content

@dataclass
class FdiskRegion:
    start_sector: int
    end_sector: int
    sectors: int
    type_id: int
    boot: bool


class FdiskParser:
    TYPE_FAT32_LBA = 0x0C
    TYPE_LINUX_NATIVE = 0x83

    is_valid: bool = False
    diskid: int = None
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
        Disk image: 5,1 MiB, 5250560 bytes, 10255 sectors
        Units: sectors of 1 * 512 = 512 bytes
        Sector size (logical/physical): 512 bytes / 512 bytes
        I/O size (minimum/optimal): 512 bytes / 512 bytes
        Disklabel type: dos
        Disk identifier: 0x5a30abff

        Device                                                 Boot Start   End Sectors Size Id Type
        image1 *       13    14       2   1K 83 Linux
        image2         15 10254   10240   5M  b W95 FAT32

        """
        in_regions = False
        for line in output.splitlines():
            if in_regions:
                parts = re.split(r"\s+", line)
                if not parts[1] == "*":
                    parts.insert(1, "")
                _, boot, start, end, sectors, _, tyoe_id, *_ = parts
                self.regions.append(FdiskRegion(
                    int(start),
                    int(end),
                    int(sectors),
                    int(tyoe_id, 16),
                    boot == "*"
                ))

            else:
                if line.startswith("Disk identifier:"):
                    self.diskid = int(line.split(":")[1], 16)
                elif line.startswith("Device"):
                    in_regions = True


class TestMBR:
    def test_empty(self, tmp_path: Path):
        image = tmp_path / "image"
        obj = MBR()

        obj.prepare()
        obj.create(image)

        assert image.stat().st_size == 512

        ret = subprocess.run([
            'fdisk',
            '-l',
            image
        ], stdout=subprocess.PIPE, check=False)

        assert ret.returncode == 0

    def test_diskid(self, tmp_path):
        image = tmp_path / "image"
        obj = MBR()

        obj.diskid = 0xdeadbeef
        assert obj.diskid == 0xdeadbeef

        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)

        assert fdisk.is_valid
        assert fdisk.diskid == 0xdeadbeef

    def test_withParts(self, tmp_path):
        BuildLocation()(tmp_path)

        image = tmp_path / "image"
        obj = MBR()

        empty = EmptyRegion()
        empty.name = "empty region"
        empty.start = SizeType(512 * 12)
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
        assert fdisk.regions[0].start_sector == 13
        assert fdisk.regions[0].type_id == FdiskParser.TYPE_LINUX_NATIVE
        assert fdisk.regions[1].start_sector == 15
        assert fdisk.regions[1].type_id == FdiskParser.TYPE_FAT32_LBA
