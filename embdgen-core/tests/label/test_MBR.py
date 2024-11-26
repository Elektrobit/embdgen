# SPDX-License-Identifier: GPL-3.0-only

from pathlib import Path
import subprocess

from embdgen.core.utils.image import BuildLocation
from embdgen.core.utils.SizeType import SizeType

from embdgen.plugins.content.EmptyContent import EmptyContent
from embdgen.plugins.label.MBR import MBR
from embdgen.plugins.region.EmptyRegion import EmptyRegion
from embdgen.plugins.region.PartitionRegion import PartitionRegion

from embdgen.plugins.content.RawContent import RawContent
from embdgen.plugins.content.FilesContent import FilesContent
from embdgen.plugins.content.Fat32Content import Fat32Content

from ..test_utils.FdiskParser import FdiskParser, FdiskRegion


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
        assert fdisk.diskid == "0xdeadbeef"

    def test_withParts(self, tmp_path):
        BuildLocation().set_path(tmp_path)

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
        assert fdisk.regions[0].type_id == FdiskRegion.TYPE_LINUX_NATIVE
        assert fdisk.regions[0].boot
        assert fdisk.regions[1].start_sector == 15
        assert fdisk.regions[1].type_id == FdiskRegion.TYPE_FAT32_LBA

    def test_four_partitions_no_extended(self, tmp_path: Path):
        BuildLocation().set_path(tmp_path)
        image = tmp_path / "image"
        obj = MBR()

        for i in range(4):
            part = PartitionRegion()
            part.name = f"Part {i}"
            part.size = SizeType.parse("1MB")
            part.fstype = "ext4"
            part.content = EmptyContent()
            obj.parts.append(part)
        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)
        assert fdisk.is_valid
        assert len(fdisk.regions) == 4
        for i in range(4):
            assert fdisk.regions[i].type_id == FdiskRegion.TYPE_LINUX_NATIVE

    def test_extended_with_empty(self, tmp_path: Path):
        BuildLocation().set_path(tmp_path)
        image = tmp_path / "image"
        obj = MBR()

        for i in range(8):
            if i == 4:
                part = EmptyRegion()
                part.name = f"Empty {i}"
                part.size = SizeType.parse("12 S")
            else:
                part = PartitionRegion()
                part.name = f"Part {i}"
                part.size = SizeType.parse("1MB")
                part.fstype = "ext4"
                part.content = EmptyContent()
            obj.parts.append(part)
        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)
        assert fdisk.is_valid
        assert len(fdisk.regions) == 8
        pos = 1
        for i in range(3):
            assert fdisk.regions[i].type_id == FdiskRegion.TYPE_LINUX_NATIVE
            assert fdisk.regions[i].start_sector == pos
            pos += SizeType.parse("1MB").sectors
        assert fdisk.regions[3].type_id == FdiskRegion.TYPE_EXTENDED
        for i in range(4, 8):
            pos += 1
            assert fdisk.regions[i].type_id == FdiskRegion.TYPE_LINUX_NATIVE
            assert fdisk.regions[i].start_sector == pos
            pos += SizeType.parse("1MB").sectors
            if i == 4:
                pos += 12 # Empty partition

    def test_efi_system(self, tmp_path: Path) -> None:
        image = tmp_path / "image"
        obj = MBR()        

        esp = PartitionRegion()
        esp.name = "EFI system partition"
        esp.size = SizeType.parse("100 MB")
        esp.fstype = "esp"
        esp.content = EmptyContent()

        obj.parts.append(esp)

        obj.prepare()
        obj.create(image)

        fdisk = FdiskParser(image)
        assert fdisk.is_valid
        assert fdisk.regions[0].type_id == FdiskRegion.TYPE_ESP
