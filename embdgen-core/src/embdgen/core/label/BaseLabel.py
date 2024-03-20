# SPDX-License-Identifier: GPL-3.0-only

import abc
from typing import List, Optional
from pathlib import Path
import parted # type: ignore
from typing_extensions import TypeGuard

from embdgen.plugins.region.PartitionRegion import PartitionRegion

from embdgen.core.utils.SizeType import SizeType
from embdgen.core.utils.image import create_empty_image
from ..utils.class_factory import Config
from ..region import BaseRegion


@Config('parts')
@Config('boot_partition', optional=True)
class BaseLabel(abc.ABC):
    """Base class for labels (i.e. partition types, e.g. MBR or GPT)"""

    parts: List[BaseRegion]
    """List of regions to be included in the image"""

    boot_partition: Optional[str] = None
    """Name of the partitions marked as 'bootable'"""

    def __init__(self) -> None:
        self.parts = []

    def prepare(self) -> None:
        for part in self.parts:
            part.prepare()
        self.parts.sort(key=lambda x: x.start)
        cur_offset = SizeType(0)
        for part in self.parts:
            if part.start.is_undefined:
                part.start = cur_offset
            cur_offset = part.start + part.size

        self._validate_parts()

    def _validate_parts(self) -> None:
        self.parts.sort(key=lambda x: x.start)
        cur_offset = SizeType(0)
        last_part = None
        for part in self.parts:
            if part.start < cur_offset:
                raise Exception(f"Part '{part.name}' overlapps with '{last_part.name}'") # type: ignore[attr-defined]
            last_part = part
            cur_offset += part.size

    def _create_partition_table(self, filename: Path, ptType: str) -> None:
        device = parted.getDevice(filename.as_posix())
        disk = parted.freshDisk(device, ptType)

        def is_partition(x: BaseRegion) -> TypeGuard[PartitionRegion]:
            return isinstance(x, PartitionRegion)

        partitions = list(filter(is_partition, self.parts))
        need_extended = ptType == "msdos" and len(partitions) > 4

        for partIndex, part in enumerate(partitions):
            part_type = parted.PARTITION_NORMAL
            if need_extended:
                if partIndex >= 3:
                    part_type = parted.PARTITION_LOGICAL

                if partIndex == 3:
                    # In the extended Partition Size, + 1 is added to include the size of the first EBR Header
                    extPartLen = self.parts[-1].start.sectors + self.parts[-1].size.sectors - part.start.sectors + 1

                    geometryExtended = parted.Geometry(device, start=(part.start.sectors - 1), length=extPartLen)

                    partitionExtended = parted.Partition(
                        disk=disk,
                        type=parted.PARTITION_EXTENDED,
                        geometry=geometryExtended
                    )
                    disk.addPartition(
                        partition=partitionExtended,
                        constraint=parted.Constraint(exactGeom=geometryExtended)
                    )

            geometry = parted.Geometry(device, start=part.start.sectors, length=part.size.sectors)
            partition = parted.Partition(
                disk=disk,
                type=part_type,
                geometry=geometry,
                fs=parted.FileSystem(part.fstype, geometry=geometry)
            )

            if ptType == "msdos":
                partition.setFlag(parted.PARTITION_LBA)
            disk.addPartition(partition=partition, constraint=parted.Constraint(exactGeom=geometry))
            if part.name == self.boot_partition:
                partition.setFlag(parted.PARTITION_BOOT)
        disk.commit()

    def create(self, filename: Path) -> None:
        size = self.parts[-1].start + self.parts[-1].size
        create_empty_image(filename, size.bytes)

        self.create_partition_table(filename)

        with filename.open("rb+") as f:
            for part in self.parts:
                part.write(f)

    @abc.abstractmethod
    def create_partition_table(self, filename: Path) -> None:
        pass
