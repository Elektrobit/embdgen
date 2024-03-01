# SPDX-License-Identifier: GPL-3.0-only

from typing import List
from pathlib import Path

import abc
import parted

from embdgen.plugins.region.PartitionRegion import PartitionRegion

from embdgen.core.utils.SizeType import SizeType
from embdgen.core.utils.image import create_empty_image
from embdgen.core.utils.class_factory import Config
from embdgen.core.region import BaseRegion


@Config("parts")
@Config("boot_partition", optional=True)
class BaseLabel(abc.ABC):
    """
    Base class for labels (i.e. partition types, e.g. MBR or GPT)
    """

    parts: List[BaseRegion]
    """
    List of regions to be included in the image
    """

    boot_partition: str = None
    """
    Name of the partitions marked as 'bootable'
    """

    def __init__(self):
        self.parts = []

    def prepare(self):
        for part in self.parts:
            part.prepare()

        self.parts.sort(key=lambda x: x.start)
        cur_offset = SizeType(0)

        for part in self.parts:
            if part.start.is_undefined:
                part.start = cur_offset
            cur_offset = part.start + part.size

        self._validate_parts()

    def _validate_parts(self):
        self.parts.sort(key=lambda x: x.start)
        cur_offset = SizeType(0)
        last_part = None
        for part in self.parts:
            if part.start < cur_offset:
                raise Exception(f"Part '{part.name}' overlapps with '{last_part.name}'")
            last_part = part
            cur_offset += part.size

    def _create_partition_table(self, filename: Path, ptType: str):
        device = parted.getDevice(filename.as_posix())
        disk = parted.freshDisk(device, ptType)

        for part in self.parts:
            if not isinstance(part, PartitionRegion):
                continue
            geometry = parted.Geometry(device, start=part.start.sectors, length=part.size.sectors)
            partition = parted.Partition(
                disk=disk,
                type=parted.PARTITION_NORMAL,
                geometry=geometry,
                fs=parted.FileSystem(part.fstype, geometry=geometry),
            )

            if ptType == "msdos":
                partition.setFlag(parted.PARTITION_LBA)
            disk.addPartition(partition=partition, constraint=parted.Constraint(exactGeom=geometry))

            if part.name == self.boot_partition:
                partition.setFlag(parted.PARTITION_BOOT)

        disk.commit()

    def create(self, filename: Path):
        size = self.parts[-1].start + self.parts[-1].size
        create_empty_image(filename, size.bytes)

        self.create_partition_table(filename)

        with filename.open("rb+") as f:
            for part in self.parts:
                part.write(f)

    @abc.abstractmethod
    def create_partition_table(self, filename: Path):
        pass
